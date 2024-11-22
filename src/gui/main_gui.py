# Standard library imports
import ctypes
import datetime
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, scrolledtext

#Set DPI awareness on Windows
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # System DPI Awareness
    except Exception as e:
        pass  # Handle exceptions if necessary

# Third-party imports
from ttkthemes import ThemedTk

# Local application imports
from ..workflow_manager import WorkflowManager
from ..processors.base_processor import ProcessorConfig
from ..utils.errors import (
    ProcessingError,
    APIError,
    ValidationError,
    FileError
)
class ScientificGUI(ThemedTk):
    def __init__(self):
        super().__init__(theme="arc")

        # Window setup
        
        self.title("ProtDomRetriever Suite")
        self.geometry("1200x800")
        
        # Set minimum window size
        self.minsize(width=870, height=800)
        
        # Get the scaling factor
        scaling = self.tk.call('tk', 'scaling')
        
        # Adjust base font size
        base_font_size = int(13 * scaling)  # 11 is your default font size
        self.custom_font = ('SF Pro Display', base_font_size)
        
        # Variables
        # File paths
        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        # Processing options
        self.enable_fasta_retrieval = tk.BooleanVar(value=False)
        self.enable_af_download = tk.BooleanVar(value=False)
        self.enable_pdb_trimming = tk.BooleanVar(value=False)
        # PDB related option
        self.accept_custom_pdbs = tk.BooleanVar(value=True)
        self.pdb_source_dir = tk.StringVar()
        self.custom_pdb_strict = tk.BooleanVar(value=False)
        # Progress tracking
        self.overall_progress = tk.DoubleVar(value=0)
        self.step_progress = tk.DoubleVar(value=0)
        
        # Modern macOS-like color scheme
        self.colors = {
            'primary': '#007AFF',  # Apple Blue
            'background': '#292929',  # Dark gray background
            'card': '#333333',  # Slightly lighter gray for cards
            'border': '#404040',  # Border color
            'text': '#FFFFFF',  # White text
            'text_secondary': '#999999',  # Gray text
            'button_bg': '#007AFF',  # Button background
            'button_fg': '#FFFFFF',  # Button text
            'input_bg': '#1E1E1E',  # Dark input background
            'input_fg': '#FFFFFF',  # Input text
            'progress_bar': '#007AFF',  # Progress bar color
            'progress_bg': '#1E1E1E'  # Progress bar background
        }
        
        # Configure dark mode
        self.configure(bg=self.colors['background'])
        self._setup_styles()
        
        # Create main container with padding
        main_container = ttk.Frame(self, style='Main.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create layout
        self._create_header(main_container)
        self._create_content(main_container)
        
        # Load saved configurations
        self.load_config()
        
        # Bind the cleanup method to window closing
        self.protocol("WM_DELETE_WINDOW", self._cleanup)

    def _setup_styles(self):
        """Configure styles for dark mode with dynamic font sizes"""
        style = ttk.Style(self)
        
        # Main background
        style.configure('Main.TFrame',
                        background=self.colors['background'])
        
        # Card style
        style.configure('Card.TFrame',
                        background=self.colors['card'],
                        borderwidth=1,
                        relief='solid')
        
        # Header style
        header_multiplier = 2.2
        header_font = (self.custom_font[0], int(self.custom_font[1] * header_multiplier), 'bold')
        style.configure('Header.TLabel',
                        background=self.colors['background'],
                        foreground=self.colors['text'],
                        font=header_font)
        
        # Subtitle style
        subtitle_font_size = max(int(self.custom_font[1] * 1.4), 10)  # Adjust multiplier as needed
        subtitle_font = (self.custom_font[0], subtitle_font_size)
        style.configure('Subtitle.TLabel',
                        background=self.colors['background'],
                        foreground=self.colors['text_secondary'],
                        font=subtitle_font)
        
        # Section headers
        section_font = (self.custom_font[0], int(self.custom_font[1] * 1.5), 'bold')
        style.configure('Section.TLabel',
                        background=self.colors['card'],
                        foreground=self.colors['text'],
                        font=section_font)
        
        # Progress bars
        style.configure('Modern.Horizontal.TProgressbar',
                        background=self.colors['progress_bar'],
                        troughcolor=self.colors['progress_bg'],
                        borderwidth=0,
                        thickness=6)
        
        # Entry style for dark mode
        style.configure('Dark.TEntry',
                        fieldbackground=self.colors['input_bg'],
                        foreground=self.colors['input_fg'],
                        insertcolor=self.colors['text'])
    
        # Checkbutton style
        style.configure('Dark.TCheckbutton',
                        background=self.colors['card'],
                        foreground=self.colors['text'],
                        font=self.custom_font)

    def _create_header(self, container):
        """Create header with improved styling"""
        header = ttk.Frame(container, style='Main.TFrame')
        header.pack(fill=tk.X, pady=(0, 20))
        
        # Title section (left side)
        title_frame = ttk.Frame(header, style='Main.TFrame')
        title_frame.pack(side=tk.LEFT)
        
        # Use self.custom_font for the title label
        ttk.Label(title_frame,
                  text="ProtDomRetriever Suite",
                  style='Header.TLabel').pack(anchor='w')
        
        # Adjust font size for the subtitle as well
        ttk.Label(title_frame,
                  text="Protein Domain Analysis Tool",
                  style='Subtitle.TLabel').pack(anchor='w')
                  
        # Buttons section (right side)
        button_frame = ttk.Frame(header, style='Main.TFrame')
        button_frame.pack(side=tk.RIGHT)
        
        self.stop_button = tk.Button(
            button_frame,
            text="⏹ Stop",
            font=('SF Pro Display', 12, 'bold'),
            bg=self.colors['primary'],
            fg='#000000',
            activebackground='#0056b3',
            activeforeground='#000000',
            disabledforeground='#FFFFFF',  # Try white for better visibility when disabled
            relief='flat',
            padx=20,
            pady=10,
            command=self._stop_processing,
            state='disabled'
        )
        
        self.stop_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Run button
        self.run_button = tk.Button(
            button_frame,
            text="▶ Run Analysis",
            font=(self.custom_font[0], self.custom_font[1], 'bold'),
            bg=self.colors['primary'],
            fg='#000000',  # Black text
            activebackground='#0056b3',  # Darker blue on hover
            activeforeground='#000000',
            relief='flat',
            padx=20,
            pady=10,
            command=self._start_processing
        )
        self.run_button.pack(side=tk.RIGHT)

    def _create_content(self, container):
        """Create the main content area with two columns"""
        content = ttk.Frame(container, style='Main.TFrame')
        content.pack(fill=tk.BOTH, expand=True)
        
        # Left Column - Input and settings
        left_col = ttk.Frame(content, style='Main.TFrame')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Create sections in order
        self._create_input_section(left_col)
        self._create_output_section(left_col)  # Added this line
        self._create_interpro_section(left_col)
        self._create_options_section(left_col)
        
        # Right Column - Progress and logs
        right_col = ttk.Frame(content, style='Main.TFrame')
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self._create_progress_section(right_col)
        self._create_log_section(right_col)

    def _create_card(self, parent, title):
        """Create a card-like frame with title"""
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            frame,
            text="◆ " + title,
            style='Section.TLabel'
        ).pack(anchor='w', padx=15, pady=10)
        
        return frame

    def _create_input_section(self, parent):
        """Create input configuration section"""
        frame = self._create_card(parent, "Input Configuration")
        
        input_frame = ttk.Frame(frame, style='Card.TFrame')
        input_frame.pack(fill=tk.X, padx=15, pady=10)
        
        entry = tk.Entry(
            input_frame,
            textvariable=self.input_file,
            font=self.custom_font,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['text'],
            relief='flat'
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_button = tk.Button(
            input_frame,
            text="📁",
            font=self.custom_font,
            bg=self.colors['card'],
            fg=self.colors['text'],
            activebackground=self.colors['primary'],
            activeforeground=self.colors['text'],
            relief='flat',
            padx=10,
            command=self._browse_input_file
        )
        browse_button.pack(side=tk.RIGHT)


    def _create_output_section(self, parent):
        """Create output directory configuration section"""
        frame = self._create_card(parent, "Output Directory")
        
        # Add help text
        ttk.Label(
            frame,
            text="Select directory for saving analysis results",
            foreground=self.colors['text_secondary'],
            background=self.colors['card'],
            font=self.custom_font,
            wraplength=400
        ).pack(fill=tk.X, padx=15, pady=(0, 5))
        
        output_frame = ttk.Frame(frame, style='Card.TFrame')
        output_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        # Output directory entry
        output_entry = tk.Entry(
            output_frame,
            textvariable=self.output_dir,
            font=self.custom_font,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['text'],
            relief='flat'
        )
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Browse button
        browse_output_button = tk.Button(
            output_frame,
            text="📁",
            font=self.custom_font,
            bg=self.colors['card'],
            fg=self.colors['text'],
            activebackground=self.colors['primary'],
            activeforeground=self.colors['text'],
            relief='flat',
            padx=10,
            command=self._browse_output_dir
        )
        browse_output_button.pack(side=tk.RIGHT)


    def _create_interpro_section(self, parent):
        """Create InterPro entries section"""
        frame = self._create_card(parent, "InterPro Entries")
        
        ttk.Label(
            frame,
            text="Enter InterPro entries (one per line or separated by comma)",
            foreground=self.colors['text_secondary'],
            background=self.colors['card'],
            font=self.custom_font,
            wraplength=400
        ).pack(fill=tk.X, padx=15, pady=(10, 5))
        
        self.interpro_text = tk.Text(
            frame,
            height=6,
            font=('SF Mono', 11),
            wrap=tk.WORD,
            relief='flat',
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['text'],
            selectbackground=self.colors['primary'],
            selectforeground=self.colors['text']
        )
        self.interpro_text.pack(fill=tk.X, padx=15, pady=(0, 10))

    def _create_options_section(self, parent):
        """Create options section"""
        frame = self._create_card(parent, "Optional Steps")
        
        # Step 1: Make options_frame an instance variable
        self.options_frame = ttk.Frame(frame, style='Card.TFrame')
        self.options_frame.pack(fill=tk.X, padx=15, pady=10)
       
        # Create custom checkbuttons
        self._create_custom_checkbox(
            self.options_frame,
            "🔍 Retrieve trimmed FASTA from UniProt",
            self.enable_fasta_retrieval
        )
        self._create_custom_checkbox(
            self.options_frame,
            "⬇️ Download AlphaFold structures",
            self.enable_af_download
        )
        self._create_custom_checkbox(
            self.options_frame,
            "✂️ Trim PDB structures",
            self.enable_pdb_trimming
        )
        
        # PDB files frame (keep this as it's important for organization)
        self.pdb_frame = ttk.Frame(self.options_frame, style='Card.TFrame')
        self.pdb_frame.pack(fill=tk.X, pady=2)

        # Allow local PDB files checkbox
        self.local_pdb_cb = tk.Checkbutton(
            self.options_frame,
            text="📁 Allow local PDB files",
            variable=self.accept_custom_pdbs,
            command=self._toggle_pdb_source,
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['card'],
            activebackground=self.colors['card'],
            activeforeground=self.colors['text'],
            font=self.custom_font,
            wraplength=800,
            justify=tk.LEFT
        )
        self.local_pdb_cb.pack(anchor='w', pady=2, padx=(5, 0))

        # Create final checkbox directly on options_frame (before calling_toggle_pdb_sources)
        self.confirm_pdb_cb = tk.Checkbutton(
            self.options_frame,
            text="✅ Confirm PDB file name format (e.g. P12345.pdb, A0A151MMY8.pdb, AF-P12345-F1.pdb)\n🎯 Uncheck to search for any matching accession names in filenames",
            variable=self.custom_pdb_strict,
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['card'],
            activebackground=self.colors['card'],
            activeforeground=self.colors['text'],
            font=self.custom_font,
            wraplength=600,
            justify=tk.LEFT
        )
        self.confirm_pdb_cb.pack(anchor='w', pady=2, padx=(5, 0))

        # Source directory selection
        self.pdb_source_frame = tk.Frame(
            self.options_frame,
            bg=self.colors['card'],
            borderwidth=0,
            relief='flat'
        )
        
        self.source_label = tk.Label(
            self.pdb_source_frame,
            text="PDB Source Directory:",
            bg=self.colors['card'],
            fg=self.colors['text'],
            font=self.custom_font
        )
        self.source_label.pack(side=tk.LEFT, padx=5)
        
        self.source_entry = tk.Entry(
            self.pdb_source_frame,
            textvariable=self.pdb_source_dir,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            width=30
        )
        self.source_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_button = tk.Button(
            self.pdb_source_frame,
            text="📁",
            command=self._browse_pdb_source,
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        # Initially hide source selection if needed
        self._toggle_pdb_source()

    def _create_custom_checkbox(self, parent, text, variable):
        """Create a custom styled checkbox"""
        cb = tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=self.colors['card'],
            fg=self.colors['text'],
            selectcolor=self.colors['card'],
            activebackground=self.colors['card'],
            activeforeground=self.colors['text'],
            font=self.custom_font,
            wraplength=600,
            justify=tk.LEFT
        )
        cb.pack(anchor='w', pady=2, padx=(5, 0))

    def _toggle_pdb_source(self):
        """Show/hide PDB source directory selection based on checkbox"""
        if self.accept_custom_pdbs.get():
            self.pdb_source_frame.pack(
                fill=tk.X,
                padx=(25, 5),
                before=self.confirm_pdb_cb
            )
        else:
            self.pdb_source_frame.pack_forget()

    def _browse_pdb_source(self):
        """Browse for PDB source directory"""
        directory = filedialog.askdirectory(
            title="Select PDB Source Directory",
            initialdir=self.pdb_source_dir.get() or os.path.expanduser("~")
        )
        if directory:
            self.pdb_source_dir.set(directory)

    def _create_progress_section(self, parent):
        """Create progress section"""
        frame = self._create_card(parent, "Analysis Progress")
        
        self._create_progress_bar(
            frame,
            "Overall Progress",
            self.overall_progress
        )
        
        self._create_progress_bar(
            frame,
            "Current Step",
            self.step_progress
        )

    def _create_progress_bar(self, parent, label, variable):
        """Create a progress bar with label"""
        container = ttk.Frame(parent, style='Card.TFrame')
        container.pack(fill=tk.X, padx=15, pady=5)
        
        label_frame = ttk.Frame(container, style='Card.TFrame')
        label_frame.pack(fill=tk.X)
        
        ttk.Label(
            label_frame,
            text=label,
            style='Dark.TCheckbutton'
        ).pack(side=tk.LEFT)
        
        percent_label = ttk.Label(
            label_frame,
            text="0%",
            style='Dark.TCheckbutton'
        )
        percent_label.pack(side=tk.RIGHT)
        
        ttk.Progressbar(
            container,
            mode='determinate',
            variable=variable,
            style='Modern.Horizontal.TProgressbar'
        ).pack(fill=tk.X, pady=(5, 0))

    def _create_log_section(self, parent):
        """Create log section"""
        frame = self._create_card(parent, "Processing Log")
        
        self.log_text = tk.Text(
            frame,
            height=15,
            font=('SF Mono', 11),
            wrap=tk.WORD,
            relief='flat',
            bg=self.colors['input_bg'],
            fg=self.colors['text_secondary'],
            insertbackground=self.colors['text'],
            selectbackground=self.colors['primary'],
            selectforeground=self.colors['text']
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

    def _browse_input_file(self):
        """Browse for input file"""
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.input_file.set(filename)
            self.log(f"Selected input file: {os.path.basename(filename)}")

    def _browse_output_dir(self):
        """Browse for output directory with improved handling"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir.get() or os.path.expanduser("~")
        )
        if directory:
            # Convert to Path object to normalize
            dir_path = Path(directory)
            try:
                # Create directory if it doesn't exist
                dir_path.mkdir(parents=True, exist_ok=True)
                self.output_dir.set(str(dir_path))
                self.log(f"Output directory set to: {dir_path}")
            except Exception as e:
                self.log(f"ERROR: Failed to create output directory: {e}")

    def log(self, message):
        """Add timestamped message to log"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.update_idletasks()

    def update_progress(self, overall=None, step=None):
        """Update progress bars"""
        try:
            if overall is not None:
                overall = max(0, min(100, overall))
                self.overall_progress.set(overall)
            if step is not None:
                step = max(0, min(100, step))
                self.step_progress.set(step)
            self.update_idletasks()
        except Exception as e:
            self.log(f"Error updating progress: {str(e)}")

    def enable_controls(self, enabled=True):
        """Enable or disable controls during processing"""
        state = 'normal' if enabled else 'disabled'
        
        def set_state(widget):
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        
        for widget in self.winfo_children():
            if isinstance(widget, (ttk.Button, ttk.Entry, tk.Button, tk.Entry, tk.Text)):
                set_state(widget)
            elif isinstance(widget, (ttk.Frame, tk.Frame)):
                for child in widget.winfo_children():
                    if isinstance(child, (ttk.Button, ttk.Entry, tk.Button, tk.Entry, tk.Text)):
                        set_state(child)

        # Handle PDB-specific controls
        if hasattr(self, 'local_pdb_cb'):
            set_state(self.local_pdb_cb)
        if hasattr(self, 'pdb_source_frame'):
            for child in self.pdb_source_frame.winfo_children():
                set_state(child)

    def save_config(self):
        """Save current configuration"""
        config = {
            'input_file': self.input_file.get(),
            'output_dir': self.output_dir.get(),
            'enable_fasta_retrieval': self.enable_fasta_retrieval.get(),
            'enable_af_download': self.enable_af_download.get(),
            'enable_pdb_trimming': self.enable_pdb_trimming.get(),
            'accept_custom_pdbs': self.accept_custom_pdbs.get(),
            'custom_pdb_strict': self.custom_pdb_strict.get(),
            'pdb_source_dir': self.pdb_source_dir.get(),
            'interpro_entries': self.interpro_text.get("1.0", tk.END).strip()
        }
        
        try:
            with open('config.json', 'w') as f:
                json.dump(config, f)
            self.log("Configuration saved")
        except Exception as e:
            self.log(f"Error saving configuration: {str(e)}")

    def load_config(self):
        """Load saved configuration"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                
                self.input_file.set(config.get('input_file', ''))
                self.output_dir.set(config.get('output_dir', ''))
                self.enable_fasta_retrieval.set(config.get('enable_fasta_retrieval', False))
                self.enable_af_download.set(config.get('enable_af_download', False))
                self.enable_pdb_trimming.set(config.get('enable_pdb_trimming', False))
                self.accept_custom_pdbs.set(config.get('accept_custom_pdbs', True))
                self.custom_pdb_strict.set(config.get('custom_pdb_strict', False))
                self.pdb_source_dir.set(config.get('pdb_source_dir', ''))
                
                entries = config.get('interpro_entries', '')
                if entries:
                    self.interpro_text.delete("1.0", tk.END)
                    self.interpro_text.insert("1.0", entries)
                    
                # Make sure PDB source frame visibility is correct after loading
                self._toggle_pdb_source()
                
                self.log("Configuration loaded")
        except Exception as e:
            self.log(f"Error loading configuration: {str(e)}")

    def _validate_inputs(self):
        """Validate all inputs before processing with improved output validation"""
        # Input file validation
        if not self.input_file.get():
            self.log("ERROR: No input file selected")
            return False
        
        input_path = Path(self.input_file.get())
        if not input_path.exists():
            self.log("ERROR: Input file does not exist")
            return False
        if not input_path.is_file():
            self.log("ERROR: Selected path is not a file")
            return False
        try:
            with open(input_path) as f:
                first_line = f.readline()
        except Exception as e:
            self.log(f"ERROR: Cannot read input file: {e}")
            return False
        
        # Output directory validation
        if not self.output_dir.get():
            self.log("ERROR: No output directory selected")
            return False
        
        output_path = Path(self.output_dir.get())
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log(f"ERROR: Cannot create output directory: {e}")
            return False
        
        if not os.access(str(output_path), os.W_OK):
            self.log("ERROR: Output directory is not writable")
            return False
        
        # InterPro entries validation
        entries = self.interpro_text.get("1.0", tk.END).strip()
        if not entries:
            self.log("ERROR: No InterPro entries provided")
            return False

        # PDB trimming validation
        if self.enable_pdb_trimming.get():
            # Case 1: Using custom PDB files
            if self.accept_custom_pdbs.get():
                if not self.pdb_source_dir.get():
                    self.log("ERROR: No PDB source directory selected when local PDB files are enabled")
                    return False
                pdb_source_path = Path(self.pdb_source_dir.get())
                if not pdb_source_path.exists():
                    self.log("ERROR: Selected PDB source directory does not exist")
                    return False
                if not pdb_source_path.is_dir():
                    self.log("ERROR: Selected PDB path is not a directory")
                    return False
                if not os.access(str(pdb_source_path), os.R_OK):
                    self.log("ERROR: PDB source directory is not readable")
                    return False
            # Case 2: Using AlphaFold structures
            else:
                # Check if we're downloading or if structures already exist
                af_dir = Path(self.output_dir.get()) / "alphafold_structures"
                if not self.enable_af_download.get() and not af_dir.exists():
                    self.log("ERROR: No PDB source available. Either enable AlphaFold download or specify local PDB directory")
                    return False

        return True


    def _start_processing(self):
        """Start the processing workflow"""
        if not self._validate_inputs():
            return
        
        self.enable_controls(False)
        self._update_button_states(processing=True)
        self.log("Starting analysis...")
        
        # Initialize processor with proper path handling
        output_dir = Path(self.output_dir.get())
        config = {  # Changed from ProcessorConfig to dictionary
            'accept_custom_pdbs': self.accept_custom_pdbs.get(),
            'custom_pdb_strict': self.custom_pdb_strict.get(),
            'pdb_source_dir': self.pdb_source_dir.get() if self.accept_custom_pdbs.get() else None
        }
        self.processor = WorkflowManager(
            output_dir=output_dir,
            callback=self._update_processing,
            config=config  # Pass config dictionary directly
        )
        
        # Get entries from text box
        entries = [entry.strip() for entry in
                  self.interpro_text.get("1.0", tk.END).strip().split('\n')]
              
        def run_processing():
            try:
                results = self.processor.run(
                    input_file=Path(self.input_file.get()),
                    interpro_entries=entries,
                    retrieve_fasta=self.enable_fasta_retrieval.get(),
                    download_alphafold=self.enable_af_download.get(),
                    trim_pdb=self.enable_pdb_trimming.get()
                )
                
                self.after(0, lambda: self._process_results(results))
            
            except Exception as error:
                error_msg = str(error)
                self.after(0, lambda msg=error_msg: self.log(f"ERROR: Processing failed: {msg}"))
            finally:
                self.after(0, lambda: self.enable_controls(True))
                self.after(0, lambda: self._update_button_states(processing=False))
        
        # Start processing in a separate thread
        processing_thread = threading.Thread(target=run_processing)
        processing_thread.daemon = True
        processing_thread.start()

    def _stop_processing(self):
        """Stop the current processing"""
        self.log("Stopping analysis...")
        if hasattr(self, 'processor') and self.processor is not None:
            try:
                # Signal the processor to stop
                self.processor.stop_requested = True
                self.log("Stop requested - waiting for current operations to complete...")
            except Exception as e:
                self.log(f"Error while stopping: {str(e)}")
        
        # Update UI
        self.stop_button.configure(state='disabled')
        self.run_button.configure(state='normal')

    def _update_button_states(self, processing=False):
        """Update button states based on processing status"""
        if processing:
            self.run_button.configure(state='disabled')
            self.stop_button.configure(state='normal')
        else:
            self.run_button.configure(state='normal')
            self.stop_button.configure(state='disabled')

    def _process_results(self, results):
        """Process and display the results in the GUI"""
        try:
            self.log("Processing completed successfully!")
            if results.get('fasta'):
                self.log(f"Retrieved {len(results['fasta'])} FASTA sequences")
            if results.get('alphafold'):
                self.log(f"Downloaded {len(results['alphafold'])} AlphaFold structures")
            if results.get('trimmed'):
                trimmed_count = len(results['trimmed'])
                source = "local directory" if self.accept_custom_pdbs.get() else "AlphaFold structures"
                self.log(f"Generated {trimmed_count} trimmed structures from {source}")
                
        except Exception as e:
            self.log(f"ERROR: Processing failed: {str(e)}")
        finally:
            self._update_button_states(processing=False) # Reset button states

    def _update_processing(self, step: str, progress: float):
        """Callback for processor to update GUI"""
        # Add more descriptive messages for PDB operations
        if "PDB" in step:
            if self.accept_custom_pdbs.get():
                source = f"from {Path(self.pdb_source_dir.get()).name}"
            else:
                source = "from AlphaFold directory"
            self.log(f"Processing PDB structures {source}: {step}")
        else:
            self.log(f"Progress: {step}")
        self.update_progress(overall=progress, step=progress)

    def _cleanup(self):
        """Cleanup before closing"""
        try:
            # Save current PDB source settings
            self.save_config()
            
            # Clean up any temporary PDB files if needed
            temp_pdb_dir = Path(self.output_dir.get()) / "temp_pdb_files"
            if temp_pdb_dir.exists():
                try:
                    for file in temp_pdb_dir.glob("*.pdb"):
                        file.unlink()
                    temp_pdb_dir.rmdir()
                except Exception as e:
                    self.log(f"Warning: Could not clean up temporary PDB files: {e}")
            
            self.quit()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            self.quit()

def main():
    app = ScientificGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
