import os
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from config import Config
from pdf_checker import is_pdf_searchable
from ocr_processor import process_ocr
from scanner import scan_directory_for_pdfs

# Initialize Rich Console
console = Console()

def setup_logging(log_file: Path):
    """Sets up file logging for OCR scan results."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Reconfigure basicConfig safely
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

def save_json_report(config, directories_data, files_data):
    """Saves and merges the scan details into pdf_ocr_data.json."""
    report_path = Path("pdf_ocr_data.json")
    existing_data = {"files": [], "directories": []}
    
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    existing_files = {f["original_path"]: f for f in existing_data.get("files", [])}
    existing_dirs = {d["path"]: d for d in existing_data.get("directories", [])}
    
    for f in files_data:
        existing_files[f["original_path"]] = f
        
    for d in directories_data:
        existing_dirs[d["path"]] = d
        
    total_files = list(existing_files.values())
    total_pdfs = len(total_files)
    already_searchable = sum(1 for f in total_files if f["status"] == "ALREADY_SEARCHABLE")
    ocr_succeeded = sum(1 for f in total_files if f["status"] == "OCR_SUCCESS")
    ocr_failed = sum(1 for f in total_files if f["status"] == "OCR_FAILURE" or f["status"] == "PROCESS_FAILURE")
    
    report = {
        "last_scan_time": datetime.now().isoformat(),
        "config": {
            "scan_directories": [str(d) for d in config.scan_directories],
            "ocr_subfolder": config.ocr_subfolder,
            "log_file": str(config.log_file),
            "ocr_lang": config.ocr_lang,
            "force_ocr": config.force_ocr
        },
        "stats": {
            "total_pdfs": total_pdfs,
            "already_searchable": already_searchable,
            "ocr_succeeded": ocr_succeeded,
            "ocr_failed": ocr_failed
        },
        "directories": list(existing_dirs.values()),
        "files": list(existing_files.values())
    }
    
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save JSON report: {e}")

def run_scan(config=None, console_output=True):
    """
    Runs the scan process using the provided config.
    If console_output is False, it runs silently without Rich rendering.
    """
    if config is None:
        config = Config()
        
    validation_errors = config.validate()
    if validation_errors:
        if console_output:
            console.print("[bold red]Configuration Errors found in .env:[/bold red]")
            for err in validation_errors:
                console.print(f"  - {err}")
        return False
        
    setup_logging(config.log_file)
    logging.info(f"Starting scan (console_output={console_output}) with config: {config}")
    
    if console_output:
        console.print("[bold blue]PDF OCR Scanning Utility[/bold blue]\n")
        console.print(f"Logging actions to: [yellow]{config.log_file}[/yellow]")
        console.print(f"OCR Subfolder configured as: [yellow]{config.ocr_subfolder}[/yellow]")
        console.print(f"OCR Language: [yellow]{config.ocr_lang}[/yellow]")
        console.print(f"Force OCR: [yellow]{config.force_ocr}[/yellow]\n")
        
    # Stats arrays for JSON report
    directories_data = []
    files_data = []
    
    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}")
    ]
    
    for dir_idx, scan_dir in enumerate(config.scan_directories, 1):
        if console_output:
            console.print(f"[bold cyan]Directory {dir_idx}/{len(config.scan_directories)}:[/bold cyan] {scan_dir}")
            
        pdf_files = []
        
        # Inner function to handle progress callback during scan_directory_for_pdfs
        def update_scan_status(dirs_scanned, files_scanned, pdfs_found, current_dir):
            if console_output:
                status.update(
                    f"[bold green]Indexing PDF files...[/bold green] "
                    f"Folders: [yellow]{dirs_scanned}[/yellow] | "
                    f"Files checked: [yellow]{files_scanned}[/yellow] | "
                    f"PDFs found: [green]{pdfs_found}[/green]\n"
                    f"[dim]Scanning: {current_dir}[/dim]"
                )
                
        if console_output:
            with console.status("[bold green]Indexing PDF files...") as status:
                try:
                    pdf_files = scan_directory_for_pdfs(scan_dir, config.ocr_subfolder, on_update=update_scan_status)
                except Exception as e:
                    msg = f"Error scanning directory {scan_dir}: {e}"
                    logging.error(msg)
                    console.print(f"[red]{msg}[/red]")
                    continue
        else:
            try:
                pdf_files = scan_directory_for_pdfs(scan_dir, config.ocr_subfolder, on_update=None)
            except Exception as e:
                logging.error(f"Error scanning directory {scan_dir}: {e}")
                continue
                
        total_files = len(pdf_files)
        if total_files == 0:
            if console_output:
                console.print(f"[yellow]No PDF files found in {scan_dir}[/yellow]\n")
            directories_data.append({
                "path": str(scan_dir),
                "total_files": 0,
                "already_searchable": 0,
                "ocr_succeeded": 0,
                "ocr_failed": 0,
                "status": "Completed"
            })
            continue
            
        if console_output:
            console.print(f"Found [green]{total_files}[/green] PDF files to check.\n")
            
        already_searchable_count = 0
        ocr_succeeded_count = 0
        ocr_failed_count = 0
        
        # Core processing function for single PDF
        def process_pdf_file(pdf_path, progress_cb=None):
            nonlocal already_searchable_count, ocr_succeeded_count, ocr_failed_count
            rel_path = pdf_path.relative_to(scan_dir)
            
            try:
                is_searchable = is_pdf_searchable(pdf_path)
                if is_searchable and not config.force_ocr:
                    msg = f"ALREADY SEARCHABLE: '{pdf_path}'"
                    logging.info(msg)
                    if progress_cb:
                        progress_cb(f"[cyan][ALREADY SEARCHABLE][/cyan] {rel_path}")
                    already_searchable_count += 1
                    
                    files_data.append({
                        "original_path": str(pdf_path),
                        "rel_path": str(rel_path),
                        "status": "ALREADY_SEARCHABLE",
                        "ocr_path": None,
                        "error": None,
                        "processed_at": datetime.now().isoformat()
                    })
                else:
                    ocr_reason = "FORCED OCR" if config.force_ocr else "NOT SEARCHABLE"
                    if progress_cb:
                        progress_cb(f"[yellow][{ocr_reason}][/yellow] Copying and OCR'ing {rel_path}...")
                        
                    ocr_success, ocr_msg = process_ocr(pdf_path, config.ocr_subfolder, config.ocr_lang)
                    
                    if ocr_success:
                        msg = f"OCR SUCCESS: '{pdf_path}' -> {ocr_msg}"
                        logging.info(msg)
                        if progress_cb:
                            progress_cb(f"[green][OCR SUCCESS][/green] {rel_path}")
                        ocr_succeeded_count += 1
                        
                        ocr_output_path = pdf_path.parent / config.ocr_subfolder / f"ocr_{pdf_path.name}"
                        files_data.append({
                            "original_path": str(pdf_path),
                            "rel_path": str(rel_path),
                            "status": "OCR_SUCCESS",
                            "ocr_path": str(ocr_output_path),
                            "error": None,
                            "processed_at": datetime.now().isoformat()
                        })
                    else:
                        msg = f"OCR FAILURE: '{pdf_path}' - {ocr_msg}"
                        logging.error(msg)
                        if progress_cb:
                            progress_cb(f"[red][OCR FAILURE][/red] {rel_path} - {ocr_msg}")
                        ocr_failed_count += 1
                        
                        files_data.append({
                            "original_path": str(pdf_path),
                            "rel_path": str(rel_path),
                            "status": "OCR_FAILURE",
                            "ocr_path": None,
                            "error": ocr_msg,
                            "processed_at": datetime.now().isoformat()
                        })
                        
            except Exception as e:
                msg = f"PROCESS FAILURE: '{pdf_path}' - Error checking searchability: {e}"
                logging.error(msg)
                if progress_cb:
                    progress_cb(f"[red][PROCESS FAILURE][/red] {rel_path} - Check failed: {e}")
                ocr_failed_count += 1
                
                files_data.append({
                    "original_path": str(pdf_path),
                    "rel_path": str(rel_path),
                    "status": "PROCESS_FAILURE",
                    "ocr_path": None,
                    "error": str(e),
                    "processed_at": datetime.now().isoformat()
                })
        
        # Render loop
        if console_output:
            with Progress(*progress_columns, console=console) as progress:
                task_desc = f"Scanning {scan_dir.name}"
                task_id = progress.add_task(task_desc, total=total_files, status="Starting...")
                
                for file_idx, pdf_path in enumerate(pdf_files, 1):
                    rel_path = pdf_path.relative_to(scan_dir)
                    rel_path_str = str(rel_path)
                    display_name = rel_path_str if len(rel_path_str) <= 30 else "..." + rel_path_str[-27:]
                    progress.update(task_id, description=f"Checking: {display_name}")
                    
                    process_pdf_file(pdf_path, progress_cb=progress.console.print)
                    
                    progress.update(
                        task_id, 
                        advance=1, 
                        status=f"{file_idx}/{total_files} files"
                    )
                progress.update(task_id, description=f"Completed {scan_dir.name}", status="Done!")
        else:
            for pdf_path in pdf_files:
                process_pdf_file(pdf_path, progress_cb=None)
                
        # Record directory results
        directories_data.append({
            "path": str(scan_dir),
            "total_files": total_files,
            "already_searchable": already_searchable_count,
            "ocr_succeeded": ocr_succeeded_count,
            "ocr_failed": ocr_failed_count,
            "status": "Completed"
        })
        
        if console_output:
            console.print(f"\n[bold green]Summary for {scan_dir.name}:[/bold green]")
            console.print(f"  - Total PDFs: {total_files}")
            console.print(f"  - Already Searchable: {already_searchable_count}")
            console.print(f"  - Successfully Processed (OCR / Skipped): {already_searchable_count + ocr_succeeded_count}")
            console.print(f"  - Failures: {ocr_failed_count}\n")
            
    # Save the JSON report
    save_json_report(config, directories_data, files_data)
    
    if console_output:
        console.print("[bold blue]Scanning and OCR processes completed.[/bold blue]")
    return True

def main():
    parser = argparse.ArgumentParser(description="PDF OCR Scanning Utility")
    parser.add_argument("--cli", action="store_true", help="Run the terminal progress CLI (default)")
    parser.add_argument("--dashboard", action="store_true", help="Launch the local web dashboard")
    args = parser.parse_args()
    
    # Default to CLI if no dashboard argument
    if args.dashboard:
        # Launch Dashboard Server
        try:
            from server import start_dashboard
            start_dashboard()
        except ImportError as e:
            console.print(f"[bold red]Failed to start dashboard server:[/bold red] {e}")
            sys.exit(1)
    else:
        run_scan(console_output=True)

if __name__ == "__main__":
    main()
