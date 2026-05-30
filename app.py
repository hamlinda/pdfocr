import os
import sys
import logging
from pathlib import Path
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
    # Ensure parent directory of log file exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

def main():
    console.print("[bold blue]PDF OCR Scanning Utility[/bold blue]\n")
    
    # 1. Load configuration
    config = Config()
    
    # 2. Validate configuration
    validation_errors = config.validate()
    if validation_errors:
        console.print("[bold red]Configuration Errors found in .env:[/bold red]")
        for err in validation_errors:
            console.print(f"  - {err}")
        console.print("\nPlease correct your .env file and restart.")
        sys.exit(1)
        
    # 3. Setup Logging
    setup_logging(config.log_file)
    logging.info(f"Starting PDF OCR scanning application with config: {config}")
    console.print(f"Logging actions to: [yellow]{config.log_file}[/yellow]")
    console.print(f"OCR Subfolder configured as: [yellow]{config.ocr_subfolder}[/yellow]")
    console.print(f"OCR Language: [yellow]{config.ocr_lang}[/yellow]")
    console.print(f"Force OCR: [yellow]{config.force_ocr}[/yellow]\n")
    
    # 4. Process directories
    # Setup Rich progress bar columns
    progress_columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}")
    ]
    
    for dir_idx, scan_dir in enumerate(config.scan_directories, 1):
        console.print(f"[bold cyan]Directory {dir_idx}/{len(config.scan_directories)}:[/bold cyan] {scan_dir}")
        # Use rich console status spinner to show active scanning progress
        with console.status("[bold green]Indexing PDF files...") as status:
            def update_scan_status(dirs_scanned, files_scanned, pdfs_found, current_dir):
                status.update(
                    f"[bold green]Indexing PDF files...[/bold green] "
                    f"Folders: [yellow]{dirs_scanned}[/yellow] | "
                    f"Files checked: [yellow]{files_scanned}[/yellow] | "
                    f"PDFs found: [green]{pdfs_found}[/green]\n"
                    f"[dim]Scanning: {current_dir}[/dim]"
                )
            
            try:
                pdf_files = scan_directory_for_pdfs(
                    scan_dir, 
                    config.ocr_subfolder, 
                    on_update=update_scan_status
                )
            except Exception as e:
                msg = f"Error scanning directory {scan_dir}: {e}"
                logging.error(msg)
                console.print(f"[red]{msg}[/red]")
                continue
            
        total_files = len(pdf_files)
        if total_files == 0:
            console.print(f"[yellow]No PDF files found in {scan_dir}[/yellow]\n")
            continue
            
        console.print(f"Found [green]{total_files}[/green] PDF files to check.\n")
        
        # Keep track of counts for summary
        success_count = 0
        failure_count = 0
        already_searchable_count = 0
        
        # Start Progress
        with Progress(*progress_columns, console=console) as progress:
            task_desc = f"Scanning {scan_dir.name}"
            task_id = progress.add_task(task_desc, total=total_files, status="Starting...")
            
            for file_idx, pdf_path in enumerate(pdf_files, 1):
                rel_path = pdf_path.relative_to(scan_dir)
                rel_path_str = str(rel_path)
                display_name = rel_path_str if len(rel_path_str) <= 30 else "..." + rel_path_str[-27:]
                
                progress.update(task_id, description=f"Checking: {display_name}")
                
                try:
                    # Check if file is already searchable
                    is_searchable = is_pdf_searchable(pdf_path)
                    
                    if is_searchable and not config.force_ocr:
                        msg = f"ALREADY SEARCHABLE: '{pdf_path}'"
                        logging.info(msg)
                        progress.console.print(
                            f"[cyan][ALREADY SEARCHABLE][/cyan] {rel_path}"
                        )
                        already_searchable_count += 1
                        success_count += 1
                    else:
                        ocr_reason = "FORCED OCR" if config.force_ocr else "NOT SEARCHABLE"
                        progress.console.print(
                            f"[yellow][{ocr_reason}][/yellow] Copying and OCR'ing {rel_path}..."
                        )
                        progress.update(task_id, description=f"OCR'ing: {display_name}")
                        
                        ocr_success, ocr_msg = process_ocr(pdf_path, config.ocr_subfolder, config.ocr_lang)
                        
                        if ocr_success:
                            msg = f"OCR SUCCESS: '{pdf_path}' -> {ocr_msg}"
                            logging.info(msg)
                            progress.console.print(
                                f"[green][OCR SUCCESS][/green] {rel_path}"
                            )
                            success_count += 1
                        else:
                            msg = f"OCR FAILURE: '{pdf_path}' - {ocr_msg}"
                            logging.error(msg)
                            progress.console.print(
                                f"[red][OCR FAILURE][/red] {rel_path} - {ocr_msg}"
                            )
                            failure_count += 1
                            
                except Exception as e:
                    msg = f"PROCESS FAILURE: '{pdf_path}' - Error checking searchability: {e}"
                    logging.error(msg)
                    progress.console.print(
                        f"[red][PROCESS FAILURE][/red] {rel_path} - Check failed: {e}"
                    )
                    failure_count += 1
                    
                # Update progress
                progress.update(
                    task_id, 
                    advance=1, 
                    status=f"{file_idx}/{total_files} files"
                )
                
            progress.update(task_id, description=f"Completed {scan_dir.name}", status="Done!")
            
        console.print(f"\n[bold green]Summary for {scan_dir.name}:[/bold green]")
        console.print(f"  - Total PDFs: {total_files}")
        console.print(f"  - Already Searchable: {already_searchable_count}")
        console.print(f"  - Successfully Processed (OCR / Skipped): {success_count}")
        console.print(f"  - Failures: {failure_count}\n")
        
    console.print("[bold blue]Scanning and OCR processes completed.[/bold blue]")

if __name__ == "__main__":
    main()
