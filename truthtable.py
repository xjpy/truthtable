import tkinter as tk
from tkinter import ttk
import re
import os
from tkinter import PhotoImage


class TruthTableApp:
    def __init__(self, root):
        self.root = root
        self.set_window_icon(self.root)
        self.root.title("TRUTHTABLE")
        self.root.geometry("680x580")
        
        self.truth_data = {}
        self.current_vars = []
        self.optimal_cover = []
        self.is_dark_mode = True
        
        self.apply_theme()
        self.setup_ui()
        self.root.bind("<F12>", lambda e: self.toggle_theme())
        
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

    def apply_theme(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        if self.is_dark_mode:
            self.colors = {
                'bg': "#1e1e1e", 'surf': "#262626", 'high': "#343434", 'active': "#3d3d3d",
                'brd': "#363636", 'txt': "#dadada", 
                'k1': "#3b5741", 'k1_fg': "#ffffff", 'mode_icon': "🌙"
            }
        else:
            self.colors = {
                'bg': "#ffffff", 'surf': "#f2f2f2", 'high': "#e0e0e0", 'active': "#d4d4d4",
                'brd': "#cccccc", 'txt': "#2e2e2e", 
                'k1': "#c8e6c9", 'k1_fg': "#000000", 'mode_icon': "☀️"
            }
            
        self.group_colors = ['#ff4d4d', '#4dff4d', '#ffff4d', '#4d94ff', '#ff944d', '#d94dff', '#4dffff']

        self.root.configure(bg=self.colors['bg'])
        self.style.configure('.', background=self.colors['bg'], foreground=self.colors['txt'], 
                            bordercolor=self.colors['brd'], lightcolor=self.colors['bg'], darkcolor=self.colors['bg'])
        self.style.map('.', background=[('active', self.colors['active'])])
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['txt'])
        self.style.configure('TButton', background=self.colors['high'], foreground=self.colors['txt'])
        self.style.map('TButton', background=[('active', self.colors['active'])])
        self.style.configure('TCheckbutton', background=self.colors['bg'], foreground=self.colors['txt'])
        self.style.map('TCheckbutton', background=[('active', self.colors['bg'])])
        self.style.configure('TEntry', fieldbackground=self.colors['surf'], foreground=self.colors['txt'], insertcolor=self.colors['txt'])
        self.style.configure('Treeview', background=self.colors['surf'], fieldbackground=self.colors['surf'], foreground=self.colors['txt'])
        self.style.configure('Treeview.Heading', background=self.colors['high'], foreground=self.colors['txt'])

        if hasattr(self, 'bottom_bar'):
            self.bottom_bar.configure(bg=self.colors['high'])
            self.lbl_theme_toggle.config(text=self.colors['mode_icon'], bg=self.colors['high'], fg=self.colors['txt'])
            self.lbl_min_func.config(bg=self.colors['high'], fg=self.colors['txt'])

    def toggle_theme(self, event=None):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

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
        ttk.Radiobutton(opt, text="Bin", variable=self.order_var, value="binary", command=self.generate).pack(side=tk.LEFT)
        ttk.Radiobutton(opt, text="Gray", variable=self.order_var, value="gray", command=self.generate).pack(side=tk.LEFT, padx=10)
        ttk.Button(opt, text="Pokaż Siatkę K", command=self.show_kmap).pack(side=tk.RIGHT)

        tab_frame = ttk.Frame(main)
        tab_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tab_frame, show='headings', height=10)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.bottom_bar = tk.Frame(main, bg=self.colors['high'], bd=0, relief="solid")
        self.bottom_bar.pack(fill=tk.X, pady=(10, 0))
        
        self.lbl_min_func = tk.Label(self.bottom_bar, text="", font=('Consolas', 11, 'bold'), 
                                     bg=self.colors['high'], fg=self.colors['txt'], anchor="w", padx=10, pady=5)
        self.lbl_min_func.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_copy_md = ttk.Button(self.bottom_bar, text="Kopiuj MD", command=self.copy_table_markdown)
        self.btn_copy_md.pack(side=tk.LEFT, padx=5, pady=3)
        
        self.lbl_theme_toggle = tk.Label(self.bottom_bar, text=self.colors['mode_icon'], cursor="hand2", 
                                         bg=self.colors['high'], fg=self.colors['txt'], width=4)
        self.lbl_theme_toggle.pack(side=tk.RIGHT, fill=tk.Y)
        self.lbl_theme_toggle.bind("<Button-1>", self.toggle_theme)

    def preprocess_expression(self, expr):
        expr = re.sub(r'(?i)\bXNOR\b', '#', expr); expr = re.sub(r'(?i)\bXOR\b', '^', expr)
        expr = re.sub(r'(?i)\bAND\b', '*', expr); expr = re.sub(r'(?i)\bOR\b', '+', expr)
        expr = re.sub(r'(?i)\bNOT\b', '!', expr); expr = expr.replace(' ', '')
        for _ in range(3):
            expr = re.sub(r'([A-Za-z01])([A-Za-z\(])', r'\1*\2', expr)
            expr = re.sub(r'\)([A-Za-z01\(])', r')*\1', expr)
        return expr

    def evaluate(self, expr, env):
        prec = {'!': 4, '*': 3, '^': 2, '#': 2, '+': 1, '(': 0}
        out, ops = [], []
        try:
            for t in expr:
                if t.isalpha(): out.append(env[t])
                elif t in '01': out.append(int(t))
                elif t == '(': ops.append(t)
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
        except: return 0

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
            val = i ^ (i >> 1) if self.order_var.get() == "gray" else i
            bits = tuple((val >> (n-1-j)) & 1 for j in range(n))
            env = dict(zip(self.current_vars, bits))
            res = self.evaluate(proc, env)
            self.truth_data[bits] = res
            self.tree.insert('', 'end', values=list(bits) + [res])
        self.minimize_function()

    def minimize_function(self):
        n = len(self.current_vars)
        if n > 4: self.lbl_min_func.config(text=""); self.optimal_cover = []; return
        minterms = []
        for i in range(2**n):
            bits = tuple(str((i >> (n-1-j)) & 1) for j in range(n))
            env = dict(zip(self.current_vars, [int(b) for b in bits]))
            if self.evaluate(self.preprocess_expression(self.entry_expr.get()), env) == 1:
                minterms.append(bits)
        
        if not minterms: self.lbl_min_func.config(text="f = 0"); self.optimal_cover = []; return
        if len(minterms) == 2**n: self.lbl_min_func.config(text="f = 1"); self.optimal_cover = []; return

        groups = [set() for _ in range(n + 1)]
        for m in minterms: groups[m.count('1')].add(m)
        primes = set()
        while True:
            new_groups = [set() for _ in range(len(groups) - 1)]; merged = set()
            for i in range(len(groups) - 1):
                for m1 in groups[i]:
                    for m2 in groups[i+1]:
                        diffs = [j for j in range(n) if m1[j] != m2[j]]
                        if len(diffs) == 1:
                            new_m = list(m1); new_m[diffs[0]] = '-'
                            new_groups[i].add(tuple(new_m)); merged.add(m1); merged.add(m2)
            for g in groups:
                for m in g:
                    if m not in merged: primes.add(m)
            if not any(new_groups): break
            groups = new_groups

        uncovered, cover, primes = set(minterms), [], list(primes)
        while uncovered:
            best_p = max(primes, key=lambda p: sum(1 for m in uncovered if all(p[k] == '-' or p[k] == m[k] for k in range(n))))
            cover.append(best_p)
            for m in list(uncovered):
                if all(best_p[k] == '-' or best_p[k] == m[k] for k in range(n)): uncovered.remove(m)
        self.optimal_cover = cover
        terms = []
        for p in cover:
            term = "".join([self.current_vars[i] if p[i]=='1' else f"!{self.current_vars[i]}" for i in range(n) if p[i]!='-'])
            terms.append(term if term else "1")
        self.lbl_min_func.config(text=f"f = {' + '.join(terms)}")

    def btn_temp_text(self, btn):
        old_text = btn.cget("text")
        btn.config(text="✅ Skopiowano")
        self.root.after(1500, lambda: btn.config(text=old_text))

    def copy_table_markdown(self):
        if not self.truth_data: return
        cols = self.tree["columns"]
        md = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"]*len(cols)) + "|"]
        for item in self.tree.get_children():
            v = list(self.tree.item(item, "values"))
            if v[-1] == "1": v[-1] = "**1**"
            md.append("| " + " | ".join(map(str, v)) + " |")
        self.root.clipboard_clear(); self.root.clipboard_append("\n".join(md))
        self.btn_temp_text(self.btn_copy_md)

    def show_kmap(self):
        if not self.truth_data: return
        n = len(self.current_vars)
        if n not in [2,3,4]: return

        win = tk.Toplevel(self.root); win.title("Siatka Karnaugha"); win.geometry("500x550"); win.configure(bg=self.colors['bg'])
        self.set_window_icon(win)
        
        self.kmap_canvas = tk.Canvas(win, bg=self.colors['surf'], highlightthickness=0)
        self.kmap_canvas.pack(expand=True, fill=tk.BOTH, padx=20, pady=(20, 10))
        
        bot = tk.Frame(win, bg=self.colors['high'], bd=0, relief="solid")
        bot.pack(fill=tk.X, padx=20, pady=(20, 20))
        
        self.show_groups_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bot, text="Pokaż grupy", variable=self.show_groups_var, 
               command=lambda: self.render_kmap_canvas(n, r_seq, c_seq),
               bg=self.colors['high'], # Kolor tła paska
               fg=self.colors['txt'],  # Kolor tekstu
               selectcolor=self.colors['surf'], # Kolor kwadracika wewnątrz
               activebackground=self.colors['active'], # Kolor po najechaniu
               activeforeground=self.colors['txt'],
               bd=0, highlightthickness=0).pack(side=tk.LEFT, padx=10, pady=5)
        
        btn_copy_kmap = ttk.Button(bot, text="Kopiuj MD")
        btn_copy_kmap.pack(side=tk.RIGHT, padx=10, pady=5)

        rows_v, cols_v = self.current_vars[:n//2], self.current_vars[n//2:]
        def gray(m): return [(0,), (1,)] if m == 1 else [(0,0), (0,1), (1,1), (1,0)]
        r_seq, c_seq = gray(len(rows_v)), gray(len(cols_v))

        self.kmap_canvas.bind("<Configure>", lambda e: self.render_kmap_canvas(n, r_seq, c_seq))
        btn_copy_kmap.config(command=lambda: self.copy_kmap_md(n, r_seq, c_seq, btn_copy_kmap))

    def render_kmap_canvas(self, n, r_seq, c_seq):
        self.kmap_canvas.delete("all")
        w, h = self.kmap_canvas.winfo_width(), self.kmap_canvas.winfo_height()
        if w < 50 or h < 50: return
        off_x, off_y = w * 0.15, h * 0.15
        cw, ch = (w - off_x) / len(c_seq), (h - off_y) / len(r_seq)

        for i, rv in enumerate(r_seq):
            for j, cv in enumerate(c_seq):
                val = 0
                for k, v in self.truth_data.items():
                    if k == rv + cv: val = v; break
                x1, y1 = off_x + j * cw, off_y + i * ch
                self.kmap_canvas.create_rectangle(x1, y1, x1+cw, y1+ch, outline=self.colors['brd'], fill=self.colors['k1'] if val == 1 else self.colors['bg'])
                self.kmap_canvas.create_text(x1+cw/2, y1+ch/2, text=str(val), fill=self.colors['k1_fg'] if val == 1 else self.colors['txt'], font=("Consolas", 14, "bold" if val==1 else "normal"))

        self.kmap_canvas.create_text(off_x/2, off_y/2, text=f"{''.join(self.current_vars[:n//2])}\\{''.join(self.current_vars[n//2:])}", fill=self.colors['txt'], font=("Consolas", 10, "bold"))
        for j, cv in enumerate(c_seq):
            self.kmap_canvas.create_text(off_x + j*cw + cw/2, off_y/2, text="".join(map(str, cv)), fill=self.colors['txt'], font=("Consolas", 11, "bold"))
        for i, rv in enumerate(r_seq):
            self.kmap_canvas.create_text(off_x/2, off_y + i*ch + ch/2, text="".join(map(str, rv)), fill=self.colors['txt'], font=("Consolas", 11, "bold"))

        if self.show_groups_var.get():
            for idx, pi in enumerate(self.optimal_cover):
                color = self.group_colors[idx % len(self.group_colors)]
                covered_r, covered_c = set(), set()
                for r in range(len(r_seq)):
                    for c in range(len(c_seq)):
                        mt = "".join(map(str, r_seq[r] + c_seq[c]))
                        if all(pi[k] == '-' or pi[k] == mt[k] for k in range(n)):
                            covered_r.add(r); covered_c.add(c)
                
                def get_blocks(indices, max_len):
                    if len(indices) == max_len: return [list(indices)]
                    if len(indices) == 2 and 0 in indices and max_len-1 in indices: return [[0], [max_len-1]]
                    return [list(indices)]

                r_blocks, c_blocks = get_blocks(sorted(list(covered_r)), len(r_seq)), get_blocks(sorted(list(covered_c)), len(c_seq))
                ins = (idx * 4) + 6
                for rb in r_blocks:
                    for cb in c_blocks:
                        x1, y1 = off_x + min(cb)*cw + ins, off_y + min(rb)*ch + ins
                        x2, y2 = off_x + (max(cb)+1)*cw - ins, off_y + (max(rb)+1)*ch - ins
                        self.kmap_canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3)

    def copy_kmap_md(self, n, r_seq, c_seq, btn):
        corner = f"{''.join(self.current_vars[:n//2])}\\{''.join(self.current_vars[n//2:])}"
        headers = [corner] + ["".join(map(str, c)) for c in c_seq]
        md = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        for r_val in r_seq:
            row = ["".join(map(str, r_val))]
            for c_val in c_seq:
                val = 0
                for k, v in self.truth_data.items():
                    if k == r_val + c_val: val = v; break
                row.append("**1**" if val == 1 else "0")
            md.append("| " + " | ".join(row) + " |")
        self.root.clipboard_clear(); self.root.clipboard_append("\n".join(md))
        self.btn_temp_text(btn)

if __name__ == "__main__":
    root = tk.Tk(); app = TruthTableApp(root); root.mainloop()