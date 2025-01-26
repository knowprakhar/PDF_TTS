import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import pdfplumber
import pyttsx3
import threading
from pdf2image import convert_from_path
import pytesseract
import tempfile
import os
from PIL import Image

class PDFReaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Prakhar's PDF TTS")
        self.root.geometry("1200x1000")
        
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # Speech speed
        self.is_speaking = False
        self.current_text = ""
        self.stop_speaking_flag = False
        
        # Configure OCR settings
        self.tessdata_dir = None  # Custom Tesseract data path if needed
        self.ocr_language = 'eng'  # Default OCR language
        
        # Create GUI components
        self.create_widgets()
        
        # Set default output folder for temporary files
        self.temp_dir = tempfile.gettempdir()

    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # File selection panel
        file_frame = ttk.LabelFrame(main_frame, text="PDF File Selection")
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Label(file_frame, text="PDF Path:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(file_frame, textvariable=self.file_path, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="OCR Settings", command=self.show_ocr_settings).pack(side=tk.LEFT, padx=5)

        # Page controls panel
        control_frame = ttk.LabelFrame(main_frame, text="Reading Controls")
        control_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(control_frame, text="Start Page:").pack(side=tk.LEFT, padx=5)
        self.page_spin = ttk.Spinbox(control_frame, from_=1, to=10000, width=6)
        self.page_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Start Line:").pack(side=tk.LEFT, padx=5)
        self.line_spin = ttk.Spinbox(control_frame, from_=1, to=10000, width=6)
        self.line_spin.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Extract Text", command=self.process_pdf).pack(side=tk.LEFT, padx=10)
        
        # Speech controls
        speech_frame = ttk.Frame(control_frame)
        speech_frame.pack(side=tk.RIGHT, padx=10)
        
        self.btn_speak = ttk.Button(speech_frame, text="▶ Speak", command=self.toggle_speech)
        self.btn_speak.pack(side=tk.LEFT, padx=2)
        ttk.Button(speech_frame, text="■ Stop", command=self.stop_speaking).pack(side=tk.LEFT, padx=2)

        # Text display area
        text_frame = ttk.LabelFrame(main_frame, text="Extracted Text")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Arial', 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def browse_file(self):
        file_types = [("PDF Files", "*.pdf"), ("All Files", "*.*")]
        filepath = filedialog.askopenfilename(filetypes=file_types)
        if filepath:
            self.file_path.set(filepath)
            self.page_spin.delete(0, 'end')
            self.page_spin.insert(0, '1')
            self.line_spin.delete(0, 'end')
            self.line_spin.insert(0, '1')

    def show_ocr_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("OCR Settings")
        
        ttk.Label(settings_win, text="Tesseract Language:").grid(row=0, column=0, padx=5, pady=5)
        self.lang_entry = ttk.Entry(settings_win)
        self.lang_entry.insert(0, self.ocr_language)
        self.lang_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_win, text="Custom Tesseract Path:").grid(row=1, column=0, padx=5, pady=5)
        self.tess_path_entry = ttk.Entry(settings_win)
        if self.tessdata_dir:
            self.tess_path_entry.insert(0, self.tessdata_dir)
        self.tess_path_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(settings_win, text="Save", command=lambda: self.save_ocr_settings(
            self.lang_entry.get(),
            self.tess_path_entry.get()
        )).grid(row=2, column=1, padx=5, pady=5)

    def save_ocr_settings(self, language, tess_path):
        self.ocr_language = language
        self.tessdata_dir = tess_path if tess_path.strip() else None
        if self.tessdata_dir:
            pytesseract.pytesseract.tesseract_cmd = tess_path
        messagebox.showinfo("Settings Saved", "OCR settings updated successfully")

    def process_pdf(self):
        self.text_area.delete(1.0, tk.END)
        self.current_text = ""
        self.update_status("Processing PDF...")
        
        pdf_path = self.file_path.get()
        if not pdf_path:
            self.update_status("No PDF file selected", error=True)
            return
            
        try:
            start_page = int(self.page_spin.get())
            start_line = int(self.line_spin.get())
            
            # Try normal text extraction first
            text = self.extract_text(pdf_path, start_page)
            
            # Fallback to OCR if no text found
            if not text.strip():
                self.update_status("No text found, attempting OCR...")
                text = self.perform_ocr(pdf_path, start_page)
                
            if not text.strip():
                self.update_status("No text could be extracted", error=True)
                return
                
            self.display_text(text, start_line)
            self.current_text = self.clean_text_for_speech(text)
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}", error=True)
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

    def extract_text(self, pdf_path, page_number):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_number < 1 or page_number > len(pdf.pages):
                    raise ValueError(f"Invalid page number. Document has {len(pdf.pages)} pages.")
                
                page = pdf.pages[page_number - 1]
                return page.extract_text()
        except Exception as e:
            self.update_status(f"Text extraction failed: {str(e)}")
            return ""

    def perform_ocr(self, pdf_path, page_number):
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                images = convert_from_path(
                    pdf_path,
                    first_page=page_number,
                    last_page=page_number,
                    output_folder=temp_dir,
                    fmt="jpeg",
                    poppler_path=self.get_poppler_path()
                )
                
                if not images:
                    raise ValueError("No images generated from PDF page")
                
                # Configure Tesseract
                tess_config = f'--tessdata-dir "{self.tessdata_dir}"' if self.tessdata_dir else ''
                text = pytesseract.image_to_string(
                    images[0],
                    lang=self.ocr_language,
                    config=tess_config
                )
                
                return text
                
        except Exception as e:
            self.update_status(f"OCR failed: {str(e)}", error=True)
            return ""

    def display_text(self, text, start_line):
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if start_line < 1 or start_line > len(lines):
            self.update_status(f"Invalid start line. Document has {len(lines)} lines.", error=True)
            return
            
        output = []
        for idx, line in enumerate(lines[start_line - 1:], start=start_line):
            output.append(f"Line {idx}: {line}")
            
        self.text_area.insert(tk.INSERT, "\n".join(output))
        self.update_status(f"Successfully extracted {len(output)} lines")

    def clean_text_for_speech(self, text):
        return '\n'.join(line.split(": ", 1)[-1] for line in text.split('\n'))

    def toggle_speech(self):
        if not self.current_text:
            self.update_status("No text available for speech", error=True)
            return
            
        if self.is_speaking:
            self.engine.stop()
            self.is_speaking = False
            self.btn_speak.config(text="▶ Speak")
            self.update_status("Speech paused")
        else:
            self.is_speaking = True
            self.btn_speak.config(text="⏸ Pause")
            threading.Thread(target=self.speak_text, daemon=True).start()

    def speak_text(self):
        try:
            self.engine.say(self.current_text)
            self.engine.runAndWait()
        except Exception as e:
            self.update_status(f"Speech error: {str(e)}", error=True)
        finally:
            self.is_speaking = False
            self.btn_speak.config(text="▶ Speak")
            self.update_status("Ready")

    def stop_speaking(self):
        self.engine.stop()
        self.is_speaking = False
        self.btn_speak.config(text="▶ Speak")
        self.update_status("Speech stopped")

    def update_status(self, message, error=False):
        self.status_bar.config(text=message)
        if error:
            self.status_bar.config(foreground='red')
        else:
            self.status_bar.config(foreground='black')

    def get_poppler_path(self):
        # Add platform-specific poppler paths here if needed
        return None

    def on_close(self):
        self.engine.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFReaderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()