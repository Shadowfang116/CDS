"""
DOCX to PDF conversion service using LibreOffice headless.
Phase 8: configurable timeout, process-group kill on timeout, LO_TIMEOUT error code.
"""
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, Any

from app.core.config import settings

# Error codes for failure surfacing
LO_TIMEOUT = "LO_TIMEOUT"
LO_CONVERSION_FAILED = "LO_CONVERSION_FAILED"
LO_UNEXPECTED = "LO_UNEXPECTED"


class DocConvertError(Exception):
    """Raised when DOCX conversion fails. Phase 8: optional error_code for API surfacing."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code or LO_UNEXPECTED


def convert_docx_bytes_to_pdf(
    docx_bytes: bytes,
    filename: str,
    timeout_seconds: Optional[int] = None,
) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Convert DOCX bytes to PDF using LibreOffice headless.
    
    Args:
        docx_bytes: The DOCX file content as bytes
        filename: Original filename (for logging/error messages)
        timeout_seconds: Maximum time to wait for conversion (default from DOC_CONVERT_TIMEOUT_SECONDS, 90)
    
    Returns:
        Tuple of (pdf_bytes, pdf_filename, metadata_dict)
        - pdf_bytes: The converted PDF content as bytes
        - pdf_filename: Suggested filename for the PDF (original_name.pdf)
        - metadata: Dict with keys: processing_seconds, converter, original_filename
    
    Raises:
        DocConvertError: If conversion fails (error_code LO_TIMEOUT on timeout).
    """
    timeout = timeout_seconds if timeout_seconds is not None else settings.DOC_CONVERT_TIMEOUT_SECONDS
    start_time = time.time()
    temp_dir = None
    input_path = None
    output_path = None
    proc = None

    try:
        # Create temporary directory for conversion
        temp_dir = tempfile.mkdtemp(prefix="docx_convert_")
        temp_path = Path(temp_dir)
        
        # Ensure output directory exists
        temp_path.mkdir(parents=True, exist_ok=True)
        
        # Write DOCX bytes to temporary file
        input_path = temp_path / f"input_{int(time.time())}.docx"
        with open(input_path, "wb") as f:
            f.write(docx_bytes)
        
        # Determine output path (LibreOffice will create input.pdf)
        output_path = temp_path / f"{input_path.stem}.pdf"
        
        # Set environment variables to avoid profile/permission issues
        env = os.environ.copy()
        env["HOME"] = "/tmp"
        env["USER"] = "nobody"
        env["TMPDIR"] = "/tmp"
        # XDG dirs to avoid permission issues
        env["XDG_CONFIG_HOME"] = "/tmp/.config"
        env["XDG_DATA_HOME"] = "/tmp/.local/share"
        env["XDG_CACHE_HOME"] = "/tmp/.cache"
        env["XDG_RUNTIME_DIR"] = "/tmp"
        # Use a dedicated LO profile to avoid conflicts
        lo_profile_dir = temp_path / "lo-profile"
        lo_profile_dir.mkdir(exist_ok=True)
        lo_profile_uri = f"file://{lo_profile_dir}"
        
        # Run LibreOffice conversion
        # --headless: Run without GUI
        # --nologo: Don't show splash screen
        # --nolockcheck: Don't check for file locks
        # --nodefault: Don't load default document
        # --nofirststartwizard: Skip first-run wizard
        # --convert-to pdf: Convert to PDF
        # --outdir: Output directory
        # -env:UserInstallation: Use dedicated profile
        cmd = [
            "soffice",
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            "--norestore",
            f"-env:UserInstallation={lo_profile_uri}",
            "--convert-to", "pdf",
            "--outdir", str(temp_path),
            str(input_path)
        ]
        
        # Run with timeout; use Popen + communicate so we can kill process group on timeout
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                start_new_session=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    if os.name != "nt" and proc.pid:
                        os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
                proc.wait()
                raise DocConvertError(
                    f"Document conversion timed out after {timeout} seconds. "
                    "The document may be too large or complex. Please try a smaller file.",
                    error_code=LO_TIMEOUT,
                )
        except DocConvertError:
            raise
        except Exception as e:
            raise DocConvertError(
                f"Failed to start conversion process: {str(e)}. "
                "Please ensure the document is a valid DOCX file.",
                error_code=LO_UNEXPECTED,
            )

        result = subprocess.CompletedProcess(cmd, proc.returncode, stdout=stdout, stderr=stderr)

        # Check if output PDF was created
        if not output_path.exists():
            error_msg = "Conversion failed: PDF output file was not created."
            if result.stdout:
                # Truncate stdout to safe length (500 chars)
                stdout_preview = result.stdout[:500].replace("\n", " ").replace("\r", "")
                error_msg += f" Stdout: {stdout_preview}"
            if result.stderr:
                # Truncate stderr to safe length (500 chars)
                stderr_preview = result.stderr[:500].replace("\n", " ").replace("\r", "")
                error_msg += f" Stderr: {stderr_preview}"
            if result.returncode != 0:
                error_msg += f" Exit code: {result.returncode}"
            raise DocConvertError(error_msg, error_code=LO_CONVERSION_FAILED)
        
        # Read PDF bytes
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Validate PDF is non-empty
        if len(pdf_bytes) == 0:
            raise DocConvertError(
                "Conversion failed: Generated PDF is empty. "
                "The document may be corrupted or unsupported.",
                error_code=LO_CONVERSION_FAILED,
            )

        # Validate PDF header (starts with %PDF)
        if not pdf_bytes.startswith(b"%PDF"):
            raise DocConvertError(
                "Conversion failed: Generated file does not appear to be a valid PDF. "
                "The document may be corrupted or unsupported.",
                error_code=LO_CONVERSION_FAILED,
            )
        
        # Calculate processing time
        processing_seconds = round(time.time() - start_time, 2)
        
        # Generate PDF filename
        original_name = Path(filename).stem
        pdf_filename = f"{original_name}.pdf"
        
        # Build metadata
        metadata = {
            "processing_seconds": processing_seconds,
            "converter": "libreoffice",
            "original_filename": filename,
            "original_size_bytes": len(docx_bytes),
            "converted_size_bytes": len(pdf_bytes),
        }
        
        return pdf_bytes, pdf_filename, metadata
        
    except DocConvertError:
        raise
    except Exception as e:
        code = getattr(e, "error_code", None) or LO_UNEXPECTED
        raise DocConvertError(
            f"Unexpected error during document conversion: {str(e)}. "
            "Please try again or contact support if the issue persists.",
            error_code=code,
        )
    finally:
        # Clean up temporary files
        if input_path and input_path.exists():
            try:
                input_path.unlink()
            except Exception:
                pass
        
        if output_path and output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                # Remove any remaining files in temp dir
                for item in Path(temp_dir).iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            import shutil
                            shutil.rmtree(item)
                    except Exception:
                        pass
                # Remove temp dir itself
                os.rmdir(temp_dir)
            except Exception:
                pass

