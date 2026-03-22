import tkinter as tk
from tkinter import ttk
import re
import os
from tkinter import PhotoImage


# ──────────────────────────────────────────────
#  Gray-code sequences for K-map axes
# ──────────────────────────────────────────────
def gray_seq(bits):
    """Return Gray-code tuples for `bits` variables."""
    if bits == 1:
        return [(0,), (1,)]
    if bits == 2:
        return [(0,0), (0,1), (1,1), (1,0)]
    if bits == 3:
        return [(0,0,0),(0,0,1),(0,1,1),(0,1,0),(1,1,0),(1,1,1),(1,0,1),(1,0,0)]
    return []


# ──────────────────────────────────────────────
#  5-variable single-grid sequences
#  4 rows (AB) × 8 cols (CDE)
# ──────────────────────────────────────────────
KMAP5_ROW_SEQ = [(0,0),(0,1),(1,1),(1,0)]          # AB  Gray
KMAP5_COL_SEQ = [                                    # CDE Gray
    (0,0,0),(0,0,1),(0,1,1),(0,1,0),
    (1,1,0),(1,1,1),(1,0,1),(1,0,0),
]

# The 5 symmetry axes, described as tuples:
#   (label, axis_type, positions)
# axis_type: 'col_fold' | 'col_wrap' | 'row_wrap' | 'col_adj' | 'row_adj'
KMAP5_AXES = [
    # variable, description visible on diagram
    ('A', 'row_wrap',   'obrót pionowy: wiersz 0 ↔ wiersz 3'),
    ('B', 'row_adj',    'sąsiednie pary: wiersze 0↔1, 2↔3'),
    ('C', 'col_fold',   'złożenie środkowe: kol 3↔4  i  kol 7↔0'),
    ('D', 'col_adj_d',  'sąsiednie pary: kol 1↔2, 5↔6'),
    ('E', 'col_adj_e',  'sąsiednie pary: kol 0↔1, 2↔3, 4↔5, 6↔7'),
]


# ──────────────────────────────────────────────
#  Quine-McCluskey minimiser  (works for n=2..5)
# ──────────────────────────────────────────────
def minimize_from_minterms(minterms_int, n, var_names):
    if not minterms_int:
        return [], "f = 0"
    if len(minterms_int) == 2**n:
        return [], "f = 1"

    def int_to_bits(i):
        return tuple(str((i >> (n-1-j)) & 1) for j in range(n))

    minterms = [int_to_bits(i) for i in minterms_int]
    groups = [set() for _ in range(n+1)]
    for m in minterms:
        groups[m.count('1')].add(m)

    primes = set()
    while True:
        new_groups = [set() for _ in range(len(groups)-1)]
        merged = set()
        for i in range(len(groups)-1):
            for m1 in groups[i]:
                for m2 in groups[i+1]:
                    diffs = [j for j in range(n) if m1[j] != m2[j]]
                    if len(diffs) == 1:
                        new_m = list(m1); new_m[diffs[0]] = '-'
                        new_groups[i].add(tuple(new_m))
                        merged.add(m1); merged.add(m2)
        for g in groups:
            for m in g:
                if m not in merged:
                    primes.add(m)
        if not any(new_groups):
            break
        groups = new_groups

    uncovered = set(minterms); cover = []; primes_list = list(primes)
    while uncovered:
        best = max(primes_list, key=lambda p: sum(
            1 for m in uncovered if all(p[k]=='-' or p[k]==m[k] for k in range(n))
        ))
        cover.append(best)
        for m in list(uncovered):
            if all(best[k]=='-' or best[k]==m[k] for k in range(n)):
                uncovered.remove(m)

    terms = []
    for p in cover:
        term = "".join(
            var_names[i] if p[i]=='1' else f"!{var_names[i]}"
            for i in range(n) if p[i] != '-'
        )
        terms.append(term if term else "1")
    return cover, "f = " + " + ".join(terms)


# ──────────────────────────────────────────────
#  Group-block decomposition for K-map drawing
# ──────────────────────────────────────────────
def kmap_blocks(indices, total):
    """
    Given a set of covered row/col indices and the total length of that axis,
    return a list of (start, end) inclusive spans.
    Handles wrap-around: if 0 and total-1 are both present, the group
    wraps across the edge and is split into two spans.
    """
    if not indices:
        return []
    s = sorted(indices)
    if len(s) == total:
        return [(0, total - 1)]
    # Single contiguous block?
    if s[-1] - s[0] == len(s) - 1:
        return [(s[0], s[-1])]
    # Wrap-around: both 0 and total-1 present, find the internal gap
    if s[0] == 0 and s[-1] == total - 1:
        for i in range(len(s) - 1):
            if s[i+1] - s[i] > 1:
                left  = (s[0],    s[i])        # 0 .. gap_start
                right = (s[i+1],  s[-1])        # gap_end .. total-1
                return [right, left]
    # fallback
    return [(s[0], s[-1])]


class TruthTableApp:

    ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def __init__(self, root):
        self.root = root
        self.set_window_icon(self.root)
        self.root.title("TRUTHTABLE")
        self.root.geometry("680x580")

        self.truth_data   = {}
        self.current_vars = []
        self.optimal_cover = []
        self.is_dark_mode = True

        self.apply_theme()
        self.setup_ui()
        self.root.bind("<F12>", lambda e: self.toggle_theme())

    # ── icon ──────────────────────────────────
    def set_window_icon(self, window):
        icon_path = "icon.png"
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                window.iconphoto(False, img)
                window._icon = img
            except Exception:
                self._set_fallback_icon(window)
        else:
            self._set_fallback_icon(window)

    def _set_fallback_icon(self, window):
        fallback = tk.PhotoImage(width=16, height=16)
        fallback.put("{#f3f3f3}", to=(0, 0, 16, 16))
        window.iconphoto(False, fallback)
        window._icon = fallback

    # ── theme ─────────────────────────────────
    def apply_theme(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        if self.is_dark_mode:
            self.colors = {
                'bg': "#1e1e1e", 'surf': "#262626", 'high': "#343434",
                'active': "#3d3d3d", 'brd': "#363636", 'txt': "#dadada",
                'k1': "#3b5741", 'k1_fg': "#ffffff", 'mode_icon': "🌙",
                'axis': "#505080",
            }
        else:
            self.colors = {
                'bg': "#ffffff", 'surf': "#f2f2f2", 'high': "#e0e0e0",
                'active': "#d4d4d4", 'brd': "#cccccc", 'txt': "#2e2e2e",
                'k1': "#c8e6c9", 'k1_fg': "#000000", 'mode_icon': "☀️",
                'axis': "#8888cc",
            }

        self.group_colors = [
            '#ff4d4d','#4dff4d','#ffff4d','#4d94ff',
            '#ff944d','#d94dff','#4dffff','#ff4daa','#aaffdd'
        ]

        self.root.configure(bg=self.colors['bg'])
        c = self.colors
        self.style.configure('.', background=c['bg'], foreground=c['txt'],
                             bordercolor=c['brd'], lightcolor=c['bg'], darkcolor=c['bg'])
        self.style.map('.', background=[('active', c['active'])])
        self.style.configure('TFrame',      background=c['bg'])
        self.style.configure('TLabel',      background=c['bg'], foreground=c['txt'])
        self.style.configure('TButton',     background=c['high'], foreground=c['txt'])
        self.style.map('TButton',           background=[('active', c['active'])])
        self.style.configure('TCheckbutton',background=c['bg'], foreground=c['txt'])
        self.style.map('TCheckbutton',      background=[('active', c['bg'])])
        self.style.configure('TEntry',      fieldbackground=c['surf'],
                             foreground=c['txt'], insertcolor=c['txt'])
        self.style.configure('Treeview',    background=c['surf'],
                             fieldbackground=c['surf'], foreground=c['txt'])
        self.style.configure('Treeview.Heading', background=c['high'], foreground=c['txt'])

        if hasattr(self, 'bottom_bar'):
            self.bottom_bar.configure(bg=c['high'])
            self.lbl_theme_toggle.config(text=c['mode_icon'], bg=c['high'], fg=c['txt'])
            self.lbl_min_func.config(bg=c['high'], fg=c['txt'])

    def toggle_theme(self, event=None):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    # ── main UI ───────────────────────────────
    def setup_ui(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(main)
        top.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top, text="f =", font=('Consolas', 12, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        self.entry_expr = ttk.Entry(top, font=('Consolas', 12))
        self.entry_expr.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_expr.bind('<Return>', lambda e: self.generate())
        ttk.Button(top, text="Generuj", width=8, command=self.generate).pack(side=tk.LEFT)

        opt = ttk.Frame(main)
        opt.pack(fill=tk.X, pady=(0, 5))
        self.order_var = tk.StringVar(value="binary")
        ttk.Radiobutton(opt, text="Bin", variable=self.order_var, value="binary",
                        command=self.generate).pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text="Gray", variable=self.order_var, value="gray",
                        command=self.generate).pack(side=tk.LEFT, padx=10)
        ttk.Button(opt, text="Pokaż Siatkę K", command=self.show_kmap).pack(side=tk.RIGHT)

        tab_frame = ttk.Frame(main)
        tab_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tab_frame, show='headings', height=10)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.bottom_bar = tk.Frame(main, bg=self.colors['high'], bd=0, relief="solid")
        self.bottom_bar.pack(fill=tk.X, pady=(10, 0))

        self.lbl_min_func = tk.Label(
            self.bottom_bar, text="", font=('Consolas', 11, 'bold'),
            bg=self.colors['high'], fg=self.colors['txt'], anchor="w", padx=10, pady=5
        )
        self.lbl_min_func.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_copy_md = ttk.Button(self.bottom_bar, text="Kopiuj MD",
                                      command=self.copy_table_markdown)
        self.btn_copy_md.pack(side=tk.LEFT, padx=5, pady=3)

        self.lbl_theme_toggle = tk.Label(
            self.bottom_bar, text=self.colors['mode_icon'], cursor="hand2",
            bg=self.colors['high'], fg=self.colors['txt'], width=4
        )
        self.lbl_theme_toggle.pack(side=tk.RIGHT, fill=tk.Y)
        self.lbl_theme_toggle.bind("<Button-1>", self.toggle_theme)

    # ── expression engine ─────────────────────
    def preprocess_expression(self, expr):
        expr = re.sub(r'(?i)\bXNOR\b', '#', expr)
        expr = re.sub(r'(?i)\bXOR\b',  '^', expr)
        expr = re.sub(r'(?i)\bAND\b',  '*', expr)
        expr = re.sub(r'(?i)\bOR\b',   '+', expr)
        expr = re.sub(r'(?i)\bNOT\b',  '!', expr)
        expr = expr.replace(' ', '')
        for _ in range(3):
            expr = re.sub(r'([A-Za-z01])([A-Za-z\(])', r'\1*\2', expr)
            expr = re.sub(r'\)([A-Za-z01\(])', r')*\1', expr)
        return expr

    def evaluate(self, expr, env):
        prec = {'!': 4, '*': 3, '^': 2, '#': 2, '+': 1, '(': 0}
        out, ops = [], []
        try:
            for t in expr:
                if t.isalpha():    out.append(env[t])
                elif t in '01':    out.append(int(t))
                elif t == '(':     ops.append(t)
                elif t == ')':
                    while ops and ops[-1] != '(': out.append(ops.pop())
                    ops.pop()
                elif t in prec:
                    while ops and ops[-1] != '(' and prec.get(ops[-1], 0) >= prec[t] and t != '!':
                        out.append(ops.pop())
                    ops.append(t)
            while ops: out.append(ops.pop())
            stack = []
            for t in out:
                if isinstance(t, int): stack.append(t)
                elif t == '!': stack.append(1 - stack.pop())
                else:
                    b, a = stack.pop(), stack.pop()
                    if t == '*': stack.append(a & b)
                    elif t == '+': stack.append(a | b)
                    elif t == '^': stack.append(a ^ b)
                    elif t == '#': stack.append(1 - (a ^ b))
            return stack[0]
        except:
            return 0

    # ── truth table generation ────────────────
    def generate(self):
        raw = self.entry_expr.get().strip()
        if not raw: return
        proc = self.preprocess_expression(raw)
        self.current_vars = sorted(list(set(re.findall(r'[A-Za-z]', proc))))
        n = len(self.current_vars)

        self.tree.delete(*self.tree.get_children())
        cols = self.current_vars + ['Wynik (Y)']
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100 if c == 'Wynik (Y)' else 60, anchor="center")

        self.truth_data = {}
        for i in range(2**n):
            val  = i ^ (i >> 1) if self.order_var.get() == "gray" else i
            bits = tuple((val >> (n-1-j)) & 1 for j in range(n))
            env  = dict(zip(self.current_vars, bits))
            res  = self.evaluate(proc, env)
            self.truth_data[bits] = res
            self.tree.insert('', 'end', values=list(bits) + [res])

        self._run_minimize_and_display()

    def _run_minimize_and_display(self):
        n = len(self.current_vars)
        if n == 0:
            self.lbl_min_func.config(text=""); self.optimal_cover = []; return
        minterms_int = [
            sum(b * (1 << (n-1-j)) for j, b in enumerate(bits))
            for bits, v in self.truth_data.items() if v == 1
        ]
        cover, text = minimize_from_minterms(minterms_int, n, self.current_vars)
        self.optimal_cover = cover
        self.lbl_min_func.config(text=text)

    def _rebuild_tree_from_truth_data(self):
        n = len(self.current_vars)
        self.tree.delete(*self.tree.get_children())
        cols = self.current_vars + ['Wynik (Y)']
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100 if c == 'Wynik (Y)' else 60, anchor="center")
        for i in range(2**n):
            val  = i ^ (i >> 1) if self.order_var.get() == "gray" else i
            bits = tuple((val >> (n-1-j)) & 1 for j in range(n))
            res  = self.truth_data.get(bits, 0)
            self.tree.insert('', 'end', values=list(bits) + [res])

    # ── copy markdown ─────────────────────────
    def btn_temp_text(self, btn):
        old = btn.cget("text")
        btn.config(text="✅ Skopiowano")
        self.root.after(1500, lambda: btn.config(text=old))

    def copy_table_markdown(self):
        if not self.truth_data: return
        cols = self.tree["columns"]
        md = ["| " + " | ".join(cols) + " |",
              "|" + "|".join(["---"] * len(cols)) + "|"]
        for item in self.tree.get_children():
            v = list(self.tree.item(item, "values"))
            if v[-1] == "1": v[-1] = "**1**"
            md.append("| " + " | ".join(map(str, v)) + " |")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(md))
        self.btn_temp_text(self.btn_copy_md)

    # ══════════════════════════════════════════
    #  K-MAP WINDOW
    # ══════════════════════════════════════════
    def show_kmap(self):
        win = tk.Toplevel(self.root)
        win.title("Siatka Karnaugha")
        win.configure(bg=self.colors['bg'])
        self.set_window_icon(win)

        # ── top bar: variable-count selector ──
        top_bar = tk.Frame(win, bg=self.colors['high'])
        top_bar.pack(fill=tk.X, padx=10, pady=(10, 0))

        tk.Label(top_bar, text="Zmienne:", bg=self.colors['high'],
                 fg=self.colors['txt'], font=('Consolas', 10)
                 ).pack(side=tk.LEFT, padx=(8, 4), pady=5)

        self._kmap_n_var = tk.IntVar()
        default_n = len(self.current_vars) if 2 <= len(self.current_vars) <= 5 else 4
        self._kmap_n_var.set(default_n)

        for nv in [2, 3, 4, 5]:
            tk.Radiobutton(
                top_bar, text=str(nv), variable=self._kmap_n_var, value=nv,
                bg=self.colors['high'], fg=self.colors['txt'],
                selectcolor=self.colors['surf'],
                activebackground=self.colors['active'], activeforeground=self.colors['txt'],
                bd=0, highlightthickness=0,
                command=lambda: self._kmap_on_n_change(win)
            ).pack(side=tk.LEFT, padx=3, pady=5)

        # ── 5-var mode toggle (visible only when n=5) ──
        self._kmap5_mode = tk.StringVar(value="single")
        self._kmap5_mode_frame = tk.Frame(top_bar, bg=self.colors['high'])
        self._kmap5_mode_frame.pack(side=tk.RIGHT, padx=8)

        tk.Label(self._kmap5_mode_frame, text="Tryb 5-var:", bg=self.colors['high'],
                 fg=self.colors['txt'], font=('Consolas', 9)
                 ).pack(side=tk.LEFT, padx=(0, 4))

        for label, val in [("Jedna siatka", "single"), ("Dwie siatki", "dual")]:
            tk.Radiobutton(
                self._kmap5_mode_frame, text=label, variable=self._kmap5_mode, value=val,
                bg=self.colors['high'], fg=self.colors['txt'],
                selectcolor=self.colors['surf'],
                activebackground=self.colors['active'], activeforeground=self.colors['txt'],
                bd=0, highlightthickness=0,
                command=lambda: self._kmap_render_dispatch()
            ).pack(side=tk.LEFT, padx=3)

        # ── canvas ─────────────────────────────
        self.kmap_canvas = tk.Canvas(win, bg=self.colors['surf'], highlightthickness=0)
        self.kmap_canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=(10, 0))

        # ── minimised function label ──────────
        self._kmap_func_label = tk.Label(
            win, text="", font=('Consolas', 11, 'bold'),
            bg=self.colors['bg'], fg=self.colors['txt'], anchor="w", padx=12, pady=4
        )
        self._kmap_func_label.pack(fill=tk.X, padx=10, pady=(4, 0))

        # ── bottom bar ────────────────────────
        bot = tk.Frame(win, bg=self.colors['high'])
        bot.pack(fill=tk.X, padx=10, pady=(6, 10))

        self.show_groups_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bot, text="Pokaż grupy", variable=self.show_groups_var,
            command=self._kmap_render_dispatch,
            bg=self.colors['high'], fg=self.colors['txt'],
            selectcolor=self.colors['surf'],
            activebackground=self.colors['active'], activeforeground=self.colors['txt'],
            bd=0, highlightthickness=0
        ).pack(side=tk.LEFT, padx=10, pady=5)

        # axes-of-symmetry toggle (only makes visual sense on single-grid mode)
        self.show_axes_var = tk.BooleanVar(value=False)
        self._axes_cb = tk.Checkbutton(
            bot, text="Pokaż osie symetrii", variable=self.show_axes_var,
            command=self._kmap_render_dispatch,
            bg=self.colors['high'], fg=self.colors['txt'],
            selectcolor=self.colors['surf'],
            activebackground=self.colors['active'], activeforeground=self.colors['txt'],
            bd=0, highlightthickness=0
        )
        self._axes_cb.pack(side=tk.LEFT, padx=2, pady=5)

        btn_copy_kmap = ttk.Button(bot, text="Kopiuj MD")
        btn_copy_kmap.pack(side=tk.RIGHT, padx=10, pady=5)

        # ── initialise data ───────────────────
        self._kmap_init_data(default_n)
        self._update_5var_ui(default_n)

        self.kmap_canvas.bind("<Configure>", lambda e: self._kmap_render_dispatch())
        btn_copy_kmap.config(command=lambda: self._kmap_copy_md(btn_copy_kmap))
        win.protocol("WM_DELETE_WINDOW", lambda: self._kmap_on_close(win))

        win.geometry("900x560" if default_n == 5 else "520x560")

    # ── show/hide 5-var controls ──────────────
    def _update_5var_ui(self, n):
        if n == 5:
            self._kmap5_mode_frame.pack(side=tk.RIGHT, padx=8)
            self._axes_cb.pack(side=tk.LEFT, padx=2, pady=5)
        else:
            self._kmap5_mode_frame.pack_forget()
            self._axes_cb.pack_forget()

    # ── helpers ───────────────────────────────
    def _kmap_init_data(self, n):
        self._kmap_n    = n
        self._kmap_vars = self.ALPHABET[:n]

        if len(self.current_vars) == n and self.truth_data:
            self.current_vars = self._kmap_vars
            self._kmap_data   = dict(self.truth_data)
        else:
            if not hasattr(self, '_kmap_data') or len(self._kmap_data) != 2**n:
                self._kmap_data = {
                    tuple((i >> (n-1-j)) & 1 for j in range(n)): 0
                    for i in range(2**n)
                }
            self.current_vars = self._kmap_vars

        self._kmap_recompute()

    def _kmap_on_n_change(self, win):
        n = self._kmap_n_var.get()
        self._kmap_n    = n
        self._kmap_vars = self.ALPHABET[:n]
        self.current_vars = self._kmap_vars
        self._kmap_data = {
            tuple((i >> (n-1-j)) & 1 for j in range(n)): 0
            for i in range(2**n)
        }
        self._kmap_recompute()
        self._update_5var_ui(n)
        win.geometry("900x560" if n == 5 else "520x560")
        self._kmap_render_dispatch()

    def _kmap_recompute(self):
        n = self._kmap_n
        minterms_int = [
            sum(b * (1 << (n-1-j)) for j, b in enumerate(bits))
            for bits, v in self._kmap_data.items() if v == 1
        ]
        cover, text = minimize_from_minterms(minterms_int, n, self._kmap_vars)
        self._kmap_cover     = cover
        self._kmap_func_text = text
        if hasattr(self, '_kmap_func_label'):
            self._kmap_func_label.config(text=text)

    # ── dispatch render ───────────────────────
    def _kmap_render_dispatch(self):
        n = self._kmap_n
        if n == 5 and self._kmap5_mode.get() == "single":
            self._kmap_render5_single()
        elif n == 5:
            self._kmap_render5_dual()
        else:
            self._kmap_render_standard(n)

    # ══════════════════════════════════════════
    #  STANDARD 2 / 3 / 4 variable render
    # ══════════════════════════════════════════
    def _kmap_render_standard(self, n):
        canvas = self.kmap_canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 50 or h < 50: return

        row_bits = n // 2
        col_bits = n - row_bits
        r_seq    = gray_seq(row_bits)
        c_seq    = gray_seq(col_bits)
        row_vars = self._kmap_vars[:row_bits]
        col_vars = self._kmap_vars[row_bits:]

        off_x = w * 0.18;  off_y = h * 0.18
        cw = (w - off_x) / len(c_seq)
        ch = (h - off_y) / len(r_seq)
        c  = self.colors

        for i, rv in enumerate(r_seq):
            for j, cv in enumerate(c_seq):
                key = rv + cv
                val = self._kmap_data.get(key, 0)
                x1 = off_x + j * cw;  y1 = off_y + i * ch
                canvas.create_rectangle(x1, y1, x1+cw, y1+ch,
                    outline=c['brd'], fill=c['k1'] if val else c['bg'])
                canvas.create_text(x1+cw/2, y1+ch/2, text=str(val),
                    fill=c['k1_fg'] if val else c['txt'],
                    font=("Consolas", 14, "bold" if val else "normal"))
                hit = canvas.create_rectangle(x1, y1, x1+cw, y1+ch, outline="", fill="")
                canvas.tag_bind(hit, "<Button-1>",
                    lambda e, k=key: self._kmap_toggle(k))

        canvas.create_text(off_x/2, off_y/2,
            text=f"{''.join(row_vars)}\\{''.join(col_vars)}",
            fill=c['txt'], font=("Consolas", 10, "bold"))
        for j, cv in enumerate(c_seq):
            canvas.create_text(off_x + j*cw + cw/2, off_y/2,
                text="".join(map(str, cv)), fill=c['txt'], font=("Consolas", 11, "bold"))
        for i, rv in enumerate(r_seq):
            canvas.create_text(off_x/2, off_y + i*ch + ch/2,
                text="".join(map(str, rv)), fill=c['txt'], font=("Consolas", 11, "bold"))

        if self.show_groups_var.get():
            self._draw_groups_standard(n, r_seq, c_seq, off_x, off_y, cw, ch)

    def _draw_groups_standard(self, n, r_seq, c_seq, off_x, off_y, cw, ch):
        canvas = self.kmap_canvas
        nr, nc = len(r_seq), len(c_seq)
        for idx, pi in enumerate(self._kmap_cover):
            color = self.group_colors[idx % len(self.group_colors)]
            covered_r, covered_c = set(), set()
            for r in range(nr):
                for col in range(nc):
                    mt = "".join(map(str, r_seq[r] + c_seq[col]))
                    if all(pi[k] == '-' or pi[k] == mt[k] for k in range(n)):
                        covered_r.add(r); covered_c.add(col)
            ins = idx * 4 + 6
            for r_start, r_end in kmap_blocks(covered_r, nr):
                for c_start, c_end in kmap_blocks(covered_c, nc):
                    x1 = off_x + c_start * cw + ins
                    y1 = off_y + r_start * ch + ins
                    x2 = off_x + (c_end + 1) * cw - ins
                    y2 = off_y + (r_end  + 1) * ch - ins
                    canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3)

    # ══════════════════════════════════════════
    #  5-VARIABLE SINGLE GRID  (4 rows × 8 cols)
    # ══════════════════════════════════════════
    def _kmap_render5_single(self):
        canvas = self.kmap_canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 80 or h < 60: return

        r_seq = KMAP5_ROW_SEQ   # AB  (4 rows)
        c_seq = KMAP5_COL_SEQ   # CDE (8 cols)
        vs    = self._kmap_vars  # [A,B,C,D,E]
        c     = self.colors

        off_x = w * 0.09
        off_y = h * 0.18
        cw = (w - off_x - 8) / 8
        ch = (h - off_y - 8) / 4

        # ── cells ─────────────────────────────
        for i, rv in enumerate(r_seq):
            for j, cv in enumerate(c_seq):
                key = rv + cv             # (A,B,C,D,E) all ints
                val = self._kmap_data.get(key, 0)
                x1  = off_x + j * cw;  y1 = off_y + i * ch
                canvas.create_rectangle(x1, y1, x1+cw, y1+ch,
                    outline=c['brd'], fill=c['k1'] if val else c['bg'])
                canvas.create_text(x1+cw/2, y1+ch/2, text=str(val),
                    fill=c['k1_fg'] if val else c['txt'],
                    font=("Consolas", 12, "bold" if val else "normal"))
                hit = canvas.create_rectangle(x1, y1, x1+cw, y1+ch, outline="", fill="")
                canvas.tag_bind(hit, "<Button-1>",
                    lambda e, k=key: self._kmap_toggle(k))

        # ── headers ───────────────────────────
        # corner
        canvas.create_text(off_x/2, off_y/2,
            text=f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}{vs[4]}",
            fill=c['txt'], font=("Consolas", 9, "bold"))
        # col headers (CDE values)
        for j, cv in enumerate(c_seq):
            canvas.create_text(off_x + j*cw + cw/2, off_y * 0.55,
                text="".join(map(str, cv)),
                fill=c['txt'], font=("Consolas", 10, "bold"))
        # row headers (AB values)
        for i, rv in enumerate(r_seq):
            canvas.create_text(off_x/2, off_y + i*ch + ch/2,
                text="".join(map(str, rv)),
                fill=c['txt'], font=("Consolas", 10, "bold"))

        # ── symmetry axes overlay ─────────────
        if self.show_axes_var.get():
            self._draw_axes_single5(off_x, off_y, cw, ch, w, h)

        # ── groups ────────────────────────────
        if self.show_groups_var.get():
            self._draw_groups_single5(r_seq, c_seq, off_x, off_y, cw, ch)

    def _draw_axes_single5(self, off_x, off_y, cw, ch, w, h):
        """Draw the 5 symmetry-axis annotations on the single-grid K-map."""
        canvas = self.kmap_canvas
        ax = self.colors['axis']
        dash = (4, 4)
        grid_right  = off_x + 8 * cw
        grid_bottom = off_y + 4 * ch

        # ── Axis A (variable 0): row wrap — row 0 ↔ row 3 ─────────────────
        # Show as a bracket at the left, connecting top and bottom edges
        bx = off_x - 6
        canvas.create_line(bx, off_y, bx, off_y + ch, fill=ax, width=2, dash=dash)
        canvas.create_line(bx, off_y + 3*ch, bx, off_y + 4*ch, fill=ax, width=2, dash=dash)
        canvas.create_line(bx - 8, off_y + ch/2, bx, off_y + ch/2, fill=ax, width=2)
        canvas.create_line(bx - 8, off_y + 3*ch + ch/2, bx, off_y + 3*ch + ch/2, fill=ax, width=2)
        canvas.create_line(bx - 8, off_y + ch/2, bx - 8, off_y + 3*ch + ch/2, fill=ax, width=2, dash=dash)
        canvas.create_text(bx - 16, (off_y + ch/2 + off_y + 3*ch + ch/2) / 2,
            text=f"{self._kmap_vars[0]}", fill=ax, font=("Consolas", 9, "bold"))

        # ── Axis B (variable 1): adjacent row pairs ────────────────────────
        # Tick marks between rows 0↔1 and 2↔3
        for row_boundary in [off_y + ch, off_y + 3*ch]:
            canvas.create_line(grid_right + 4, row_boundary, grid_right + 14, row_boundary,
                fill=ax, width=2)
        canvas.create_text(grid_right + 22, off_y + ch/2 + ch/2,
            text=f"{self._kmap_vars[1]}", fill=ax, font=("Consolas", 9, "bold"))

        # ── Axis C (variable 2): center fold (cols 3↔4) + edge wrap (7↔0) ─
        # Center fold line
        cx_fold = off_x + 4 * cw   # between col 3 and col 4
        canvas.create_line(cx_fold, off_y - 14, cx_fold, grid_bottom + 4,
            fill=ax, width=2, dash=dash)
        canvas.create_text(cx_fold, off_y - 20,
            text=f"← {self._kmap_vars[2]} →", fill=ax, font=("Consolas", 8, "bold"))
        # Edge wrap markers (left and right edges)
        for edge_x in [off_x, grid_right]:
            canvas.create_line(edge_x, off_y - 8, edge_x, grid_bottom + 8,
                fill=ax, width=1, dash=(2, 5))
        canvas.create_text(off_x - 2, grid_bottom + 16,
            text="↕ obrót C", fill=ax, font=("Consolas", 7))

        # ── Axis D (variable 3): pairs cols 1↔2, cols 5↔6 ────────────────
        for col_boundary in [off_x + 2*cw, off_x + 6*cw]:
            canvas.create_line(col_boundary, grid_bottom + 4, col_boundary, grid_bottom + 14,
                fill=ax, width=2)
        canvas.create_text(off_x + 2*cw, grid_bottom + 22,
            text=self._kmap_vars[3], fill=ax, font=("Consolas", 9, "bold"))
        canvas.create_text(off_x + 6*cw, grid_bottom + 22,
            text=self._kmap_vars[3], fill=ax, font=("Consolas", 9, "bold"))

        # ── Axis E (variable 4): adjacent column pairs every 1 step ─────────
        for j in range(8):
            cx = off_x + j * cw + cw
            if j < 7:
                canvas.create_line(cx, grid_bottom + 18, cx, grid_bottom + 26,
                    fill=ax, width=1, dash=dash)
        canvas.create_text(off_x + 8*cw/2, grid_bottom + 36,
            text=f"←— {self._kmap_vars[4]} —→", fill=ax, font=("Consolas", 8, "bold"))

    def _draw_groups_single5(self, r_seq, c_seq, off_x, off_y, cw, ch):
        """
        Draw prime-implicant group rectangles on the single 4×8 grid.
        Groups that wrap around edges are split into multiple rectangles.
        """
        canvas = self.kmap_canvas
        n = 5
        for idx, pi in enumerate(self._kmap_cover):
            color = self.group_colors[idx % len(self.group_colors)]
            covered_r = set(); covered_c = set()
            for r in range(4):
                for col in range(8):
                    # key is (A,B,C,D,E) with ints
                    mt_ints = r_seq[r] + c_seq[col]
                    mt = "".join(map(str, mt_ints))
                    if all(pi[k] == '-' or pi[k] == mt[k] for k in range(n)):
                        covered_r.add(r); covered_c.add(col)
            if not covered_r or not covered_c:
                continue
            ins = idx * 3 + 5
            for r_start, r_end in kmap_blocks(covered_r, 4):
                for c_start, c_end in kmap_blocks(covered_c, 8):
                    x1 = off_x + c_start * cw + ins
                    y1 = off_y + r_start * ch + ins
                    x2 = off_x + (c_end + 1) * cw - ins
                    y2 = off_y + (r_end  + 1) * ch - ins
                    canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3)

    # ══════════════════════════════════════════
    #  5-VARIABLE DUAL GRID  (two 4×4 grids)
    # ══════════════════════════════════════════
    def _kmap_render5_dual(self):
        canvas = self.kmap_canvas
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 100 or h < 80: return

        c     = self.colors
        r_seq = [(0,0),(0,1),(1,1),(1,0)]   # AB
        c_seq = [(0,0),(0,1),(1,1),(1,0)]   # CD
        vs    = self._kmap_vars

        margin_top  = h * 0.16
        margin_left = w * 0.08
        gap    = w * 0.06
        grid_w = (w - margin_left * 2 - gap) / 2
        grid_h = h - margin_top - 10
        cw = grid_w / 4;  ch = grid_h / 4

        for e_val in [0, 1]:
            gx = margin_left + e_val * (grid_w + gap)
            canvas.create_text(gx + grid_w/2, margin_top/2 - 12,
                text=f"{vs[4]}={e_val}", fill=c['txt'], font=("Consolas", 10, "bold"))
            for j, cv in enumerate(c_seq):
                canvas.create_text(gx + j*cw + cw/2, margin_top * 0.75,
                    text="".join(map(str, cv)), fill=c['txt'], font=("Consolas", 10, "bold"))
            for i, rv in enumerate(r_seq):
                if e_val == 0:
                    canvas.create_text(margin_left/2, margin_top + i*ch + ch/2,
                        text="".join(map(str, rv)), fill=c['txt'], font=("Consolas", 10, "bold"))
                for j, cv in enumerate(c_seq):
                    key = rv + cv + (e_val,)
                    val = self._kmap_data.get(key, 0)
                    x1 = gx + j * cw;  y1 = margin_top + i * ch
                    canvas.create_rectangle(x1, y1, x1+cw, y1+ch,
                        outline=c['brd'], fill=c['k1'] if val else c['bg'])
                    canvas.create_text(x1+cw/2, y1+ch/2, text=str(val),
                        fill=c['k1_fg'] if val else c['txt'],
                        font=("Consolas", 13, "bold" if val else "normal"))
                    hit = canvas.create_rectangle(x1, y1, x1+cw, y1+ch, outline="", fill="")
                    canvas.tag_bind(hit, "<Button-1>",
                        lambda e, k=key: self._kmap_toggle(k))

        canvas.create_text(margin_left/2, margin_top/2,
            text="AB\\CD", fill=c['txt'], font=("Consolas", 9, "bold"))

        if self.show_groups_var.get():
            self._draw_groups_dual5(r_seq, c_seq, margin_left, margin_top, gap, grid_w, cw, ch)

    def _draw_groups_dual5(self, r_seq, c_seq, margin_left, margin_top, gap, grid_w, cw, ch):
        canvas = self.kmap_canvas
        n = 5
        for idx, pi in enumerate(self._kmap_cover):
            color = self.group_colors[idx % len(self.group_colors)]
            ins = idx * 3 + 5
            for e_val in [0, 1]:
                if pi[4] not in ('-', str(e_val)): continue
                gx = margin_left + e_val * (grid_w + gap)
                covered_r, covered_c = set(), set()
                for r in range(4):
                    for col in range(4):
                        mt_bits = r_seq[r] + c_seq[col] + (e_val,)
                        mt = "".join(map(str, mt_bits))
                        if all(pi[k] == '-' or pi[k] == mt[k] for k in range(n)):
                            covered_r.add(r); covered_c.add(col)
                if not covered_r or not covered_c: continue
                for r_s, r_e in kmap_blocks(covered_r, 4):
                    for c_s, c_e in kmap_blocks(covered_c, 4):
                        x1 = gx + c_s * cw + ins;  y1 = margin_top + r_s * ch + ins
                        x2 = gx + (c_e+1)*cw - ins; y2 = margin_top + (r_e+1)*ch - ins
                        canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3)

    # ── cell toggle ───────────────────────────
    def _kmap_toggle(self, key):
        self._kmap_data[key] = 1 - self._kmap_data.get(key, 0)
        self._kmap_recompute()
        self._kmap_render_dispatch()

    # ── close → sync back to main window ─────
    def _kmap_on_close(self, win):
        self.current_vars  = list(self._kmap_vars)
        self.truth_data    = dict(self._kmap_data)
        self.optimal_cover = list(self._kmap_cover)

        func_text = self._kmap_func_text
        expr_part = func_text[4:] if func_text.startswith("f = ") else func_text
        self.entry_expr.delete(0, tk.END)
        self.entry_expr.insert(0, expr_part)
        self.lbl_min_func.config(text=func_text)
        self._rebuild_tree_from_truth_data()
        win.destroy()

    # ── copy kmap markdown ─────────────────────
    def _kmap_copy_md(self, btn):
        n = self._kmap_n; lines = []
        if n == 5:
            vs    = self._kmap_vars
            if self._kmap5_mode.get() == "single":
                r_seq = KMAP5_ROW_SEQ; c_seq = KMAP5_COL_SEQ
                header = [f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}{vs[4]}"] + \
                         ["".join(map(str, cv)) for cv in c_seq]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + "|".join(["---"]*len(header)) + "|")
                for rv in r_seq:
                    row = ["".join(map(str, rv))]
                    for cv in c_seq:
                        val = self._kmap_data.get(rv + cv, 0)
                        row.append("**1**" if val else "0")
                    lines.append("| " + " | ".join(row) + " |")
            else:
                r_seq = [(0,0),(0,1),(1,1),(1,0)]; c_seq = [(0,0),(0,1),(1,1),(1,0)]
                for e_val in [0, 1]:
                    lines.append(f"\n**{vs[4]}={e_val}**\n")
                    header = ["AB\\CD"] + ["".join(map(str, cv)) for cv in c_seq]
                    lines.append("| " + " | ".join(header) + " |")
                    lines.append("|" + "|".join(["---"]*len(header)) + "|")
                    for rv in r_seq:
                        row = ["".join(map(str, rv))]
                        for cv in c_seq:
                            val = self._kmap_data.get(rv + cv + (e_val,), 0)
                            row.append("**1**" if val else "0")
                        lines.append("| " + " | ".join(row) + " |")
        else:
            row_bits = n // 2; col_bits = n - row_bits
            r_seq = gray_seq(row_bits); c_seq = gray_seq(col_bits)
            row_vars = self._kmap_vars[:row_bits]; col_vars = self._kmap_vars[row_bits:]
            corner = f"{''.join(row_vars)}\\{''.join(col_vars)}"
            header = [corner] + ["".join(map(str, cv)) for cv in c_seq]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join(["---"]*len(header)) + "|")
            for rv in r_seq:
                row = ["".join(map(str, rv))]
                for cv in c_seq:
                    val = self._kmap_data.get(rv + cv, 0)
                    row.append("**1**" if val else "0")
                lines.append("| " + " | ".join(row) + " |")

        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.btn_temp_text(btn)


if __name__ == "__main__":
    root = tk.Tk()
    app  = TruthTableApp(root)
    root.mainloop()
