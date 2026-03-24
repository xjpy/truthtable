import tkinter as tk
from tkinter import ttk, simpledialog
import re
import os

# ──────────────────────────────────────────────
#  Gray-code sequences
# ──────────────────────────────────────────────
def gray_seq(bits):
    if bits == 1: return [(0,),(1,)]
    if bits == 2: return [(0,0),(0,1),(1,1),(1,0)]
    if bits == 3: return [(0,0,0),(0,0,1),(0,1,1),(0,1,0),(1,1,0),(1,1,1),(1,0,1),(1,0,0)]
    return []

KMAP5_ROW_SEQ = [(0,0),(0,1),(1,1),(1,0)]           # AB
KMAP5_COL_SEQ = [(0,0,0),(0,0,1),(0,1,1),(0,1,0),   # CDE
                  (1,1,0),(1,1,1),(1,0,1),(1,0,0)]
KMAP5_AXES = [
    ('A', 'obrót pionowy: wiersz 0 ↔ wiersz 3'),
    ('B', 'sąsiednie pary wierszy: 0↔1, 2↔3'),
    ('C', 'złożenie środkowe kol 3↔4  i  obrót poziomy kol 7↔0'),
    ('D', 'sąsiednie pary kol: 1↔2, 5↔6'),
    ('E', 'sąsiednie kolumny: 0↔1, 2↔3, 4↔5, 6↔7'),
]

# ──────────────────────────────────────────────
#  Quine-McCluskey SOP minimiser (n ≤ 5) with Don't Cares
# ──────────────────────────────────────────────
def minimize_from_minterms(ones_int, dcs_int, n, var_names):
    if not ones_int: return [], "f = 0"
    if len(ones_int) + len(dcs_int) == 2**n: return [], "f = 1"

    def i2b(i): return tuple(str((i>>(n-1-j))&1) for j in range(n))

    minterms = [i2b(i) for i in ones_int + dcs_int]
    groups = [set() for _ in range(n+1)]
    for m in minterms: groups[m.count('1')].add(m)

    primes = set()
    while True:
        ng = [set() for _ in range(len(groups)-1)]; merged = set()
        for i in range(len(groups)-1):
            for m1 in groups[i]:
                for m2 in groups[i+1]:
                    d=[j for j in range(n) if m1[j]!=m2[j]]
                    if len(d)==1:
                        nm=list(m1); nm[d[0]]='-'
                        ng[i].add(tuple(nm)); merged.add(m1); merged.add(m2)
        for g in groups:
            for m in g:
                if m not in merged: primes.add(m)
        if not any(ng): break
        groups = ng

    uncov=set([i2b(i) for i in ones_int])
    cover=[]; pl=list(primes)
    while uncov:
        best=max(pl,key=lambda p:sum(1 for m in uncov if all(p[k]=='-'or p[k]==m[k] for k in range(n))))
        cover.append(best)
        for m in list(uncov):
            if all(best[k]=='-'or best[k]==m[k] for k in range(n)): uncov.remove(m)

    terms=[]
    for p in cover:
        t="".join(var_names[i] if p[i]=='1' else f"!{var_names[i]}" for i in range(n) if p[i]!='-')
        terms.append(t if t else "1")
    return cover, "f = "+" + ".join(terms)


# ──────────────────────────────────────────────
#  Correct group-span decomposition
# ──────────────────────────────────────────────
def find_runs_circular(indices, total):
    if not indices: return []
    s = sorted(indices)
    if len(s)==total: return [(0, total-1)]

    runs=[]; run_s=s[0]; prev=s[0]
    for x in s[1:]:
        if x==prev+1: prev=x
        else:
            runs.append((run_s,prev)); run_s=x; prev=x
    runs.append((run_s,prev))

    if len(runs)>=2 and runs[0][0]==0 and runs[-1][1]==total-1:
        return [runs[-1], runs[0]] + runs[1:-1]

    return runs


# ══════════════════════════════════════════════
#  Main application
# ══════════════════════════════════════════════
class TruthTableApp:

    ALPHABET = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def __init__(self, root):
        self.root = root
        self.set_window_icon(self.root)
        self.root.title("TRUTHTABLE")
        self.root.geometry("680x580")

        self.truth_data    = {}
        self.current_vars  = []
        self.optimal_cover = []
        self.is_dark_mode  = True

        self.apply_theme()
        self.setup_ui()
        self.root.bind("<F12>", lambda e: self.toggle_theme())

    # ── icon ──────────────────────────────────
    def set_window_icon(self, w):
        if os.path.exists("icon.png"):
            try:
                img=tk.PhotoImage(file="icon.png"); w.iconphoto(False,img); w._icon=img; return
            except: pass
        fb=tk.PhotoImage(width=16,height=16); fb.put("{#f3f3f3}",to=(0,0,16,16))
        w.iconphoto(False,fb); w._icon=fb

    # ── theme ─────────────────────────────────
    def apply_theme(self):
        self.style=ttk.Style(); self.style.theme_use('clam')
        if self.is_dark_mode:
            self.colors={'bg':"#1e1e1e",'surf':"#262626",'high':"#343434",
                'active':"#3d3d3d",'brd':"#363636",'txt':"#dadada",
                'k1':"#3b5741",'k1_fg':"#ffffff",'mode_icon':"🌙",'axis':"#5555aa"}
        else:
            self.colors={'bg':"#ffffff",'surf':"#f2f2f2",'high':"#e0e0e0",
                'active':"#d4d4d4",'brd':"#cccccc",'txt':"#2e2e2e",
                'k1':"#c8e6c9",'k1_fg':"#000000",'mode_icon':"☀️",'axis':"#8888cc"}
        self.group_colors=['#ff4d4d','#4dff4d','#ffff4d','#4d94ff',
                           '#ff944d','#d94dff','#4dffff','#ff4daa','#aaffdd']
        c=self.colors
        self.root.configure(bg=c['bg'])
        self.style.configure('.',background=c['bg'],foreground=c['txt'],
            bordercolor=c['brd'],lightcolor=c['bg'],darkcolor=c['bg'])
        self.style.map('.',background=[('active',c['active'])])
        self.style.configure('TFrame',background=c['bg'])
        self.style.configure('TLabel',background=c['bg'],foreground=c['txt'])
        self.style.configure('TButton',background=c['high'],foreground=c['txt'])
        self.style.map('TButton',background=[('active',c['active'])])
        self.style.configure('TCheckbutton',background=c['bg'],foreground=c['txt'])
        self.style.map('TCheckbutton',background=[('active',c['bg'])])
        self.style.configure('TEntry',fieldbackground=c['surf'],foreground=c['txt'],insertcolor=c['txt'])
        self.style.configure('Treeview',background=c['surf'],fieldbackground=c['surf'],foreground=c['txt'])
        self.style.configure('Treeview.Heading',background=c['high'],foreground=c['txt'])
        if hasattr(self,'bottom_bar'):
            self.bottom_bar.configure(bg=c['high'])
            self.lbl_theme_toggle.config(text=c['mode_icon'],bg=c['high'],fg=c['txt'])
            self.lbl_min_func.config(bg=c['high'],fg=c['txt'])

    def toggle_theme(self, event=None):
        self.is_dark_mode=not self.is_dark_mode; self.apply_theme()

    # ── main UI ───────────────────────────────
    def setup_ui(self):
        main=ttk.Frame(self.root,padding="15"); main.pack(fill=tk.BOTH,expand=True)
        top=ttk.Frame(main); top.pack(fill=tk.X,pady=(0,10))
        ttk.Label(top,text="f =",font=('Consolas',12,'bold')).pack(side=tk.LEFT,padx=(0,5))
        self.entry_expr=ttk.Entry(top,font=('Consolas',12))
        self.entry_expr.pack(side=tk.LEFT,fill=tk.X,expand=True,padx=5)
        self.entry_expr.bind('<Return>',lambda e:self.generate())
        ttk.Button(top,text="Generuj",width=8,command=self.generate).pack(side=tk.LEFT)

        opt=ttk.Frame(main); opt.pack(fill=tk.X,pady=(0,5))
        self.order_var=tk.StringVar(value="binary")
        ttk.Radiobutton(opt,text="Bin",variable=self.order_var,value="binary",command=self.generate).pack(side=tk.LEFT)
        ttk.Radiobutton(opt,text="Gray",variable=self.order_var,value="gray",command=self.generate).pack(side=tk.LEFT,padx=10)
        ttk.Button(opt,text="Pokaż Siatkę K",command=self.show_kmap).pack(side=tk.RIGHT)

        tab=ttk.Frame(main); tab.pack(fill=tk.BOTH,expand=True)
        self.tree=ttk.Treeview(tab,show='headings',height=10)
        self.tree.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)

        self.bottom_bar=tk.Frame(main,bg=self.colors['high'],bd=0,relief="solid")
        self.bottom_bar.pack(fill=tk.X,pady=(10,0))
        self.lbl_min_func=tk.Label(self.bottom_bar,text="",font=('Consolas',11,'bold'),
            bg=self.colors['high'],fg=self.colors['txt'],anchor="w",padx=10,pady=5)
        self.lbl_min_func.pack(side=tk.LEFT,fill=tk.X,expand=True)
        self.btn_copy_md=ttk.Button(self.bottom_bar,text="Kopiuj MD",command=self.copy_table_markdown)
        self.btn_copy_md.pack(side=tk.LEFT,padx=5,pady=3)
        self.lbl_theme_toggle=tk.Label(self.bottom_bar,text=self.colors['mode_icon'],cursor="hand2",
            bg=self.colors['high'],fg=self.colors['txt'],width=4)
        self.lbl_theme_toggle.pack(side=tk.RIGHT,fill=tk.Y)
        self.lbl_theme_toggle.bind("<Button-1>",self.toggle_theme)

    # ── expression engine ─────────────────────
    def preprocess_expression(self, expr):
        # Zamiana słów kluczowych od najdłuższych, case-insensitive
        expr = re.sub(r'(?i)\bXNOR\b', '#', expr)
        expr = re.sub(r'(?i)\bXOR\b',  '^', expr)
        expr = re.sub(r'(?i)\bAND\b',  '*', expr)
        expr = re.sub(r'(?i)\bOR\b',   '+', expr)
        expr = re.sub(r'(?i)\bNOT\b',  '!', expr)
        expr = expr.replace('~', '!')
        expr = expr.replace(' ', '')
        return expr.upper()

    def tokenize(self, expr):
        """
        Tokenizuje wyrażenie i wstawia niejawne '*' tam gdzie potrzeba.
        Poprawnie obsługuje sekwencje takie jak !A!BC!D.

        Kluczowe zachowanie:
        - ciągi złożone WYŁĄCZNIE z wielkich liter (np. 'BC', 'ABC') są rozkładane
          na pojedyncze litery – bo w notacji logicznej !A!BC!D oznacza !A * !B * C * !D
        - zmienne z cyframi lub podkreślnikami (x1, CLK_A) pozostają nienaruszone
        - '!' po wartości wstawia implicit '*'
        """
        raw = re.findall(r'[A-Z][A-Z0-9_]*|[01]|[+*^#!()]', expr)

        # Rozwiń ciągi złożone wyłącznie z wielkich liter na pojedyncze znaki
        expanded = []
        for t in raw:
            if re.match(r'^[A-Z]{2,}$', t):
                expanded.extend(list(t))
            else:
                expanded.append(t)
        raw = expanded

        tokens = []
        for i, t in enumerate(raw):
            if i > 0:
                prev = raw[i - 1]
                # Poprzedni token kończy wartość
                prev_is_val = bool(re.match(r'^[A-Z0-9]$|^[A-Z][A-Z0-9_]+$', prev)) or prev == ')'
                # Bieżący token zaczyna wartość (zmienna, stała, nawias lub negacja)
                cur_is_start = bool(re.match(r'^[A-Z0-9]$|^[A-Z][A-Z0-9_]+$', t)) or t in ('(', '!')
                if prev_is_val and cur_is_start:
                    tokens.append('*')
            tokens.append(t)
        return tokens

    def evaluate(self, expr, env):
        tokens = self.tokenize(expr)
        # Priorytety: ! najwyższy i prawostronna łączność, potem *, ^/#, +
        prec = {'!': 4, '*': 3, '^': 2, '#': 2, '+': 1}
        out = []; ops = []
        try:
            for t in tokens:
                if t in env:
                    out.append(env[t])
                elif t in ('0', '1'):
                    out.append(int(t))
                elif t == '(':
                    ops.append(t)
                elif t == ')':
                    while ops and ops[-1] != '(':
                        out.append(ops.pop())
                    if ops: ops.pop()
                elif t in prec:
                    # Dla '!' (prawostronny): zdejmuj tylko operatory o ŚCIŚLE wyższym priorytecie
                    # Dla pozostałych (lewostronne): zdejmuj operatory o >= priorytecie
                    while (ops and ops[-1] != '(' and ops[-1] in prec and
                           (prec[ops[-1]] > prec[t] if t == '!'
                            else prec[ops[-1]] >= prec[t])):
                        out.append(ops.pop())
                    ops.append(t)
            while ops:
                out.append(ops.pop())

            stack = []
            for t in out:
                if isinstance(t, int):
                    stack.append(t)
                elif t == '!':
                    stack.append(1 - stack.pop())
                else:
                    b, a = stack.pop(), stack.pop()
                    if t == '*': stack.append(a & b)
                    elif t == '+': stack.append(a | b)
                    elif t == '^': stack.append(a ^ b)
                    elif t == '#': stack.append(1 - (a ^ b))
            return stack[0] if stack else 0
        except Exception:
            return 0

    # ── truth table ───────────────────────────
    def generate(self):
        raw = self.entry_expr.get().strip()
        if not raw: return
        proc = self.preprocess_expression(raw)

        # Wyciągnij zmienne z tokenów (po preprocess słowa kluczowe są już symbolami,
        # a tokenize rozwinął wieloliterowe ciągi na pojedyncze litery)
        all_tokens = self.tokenize(proc)
        vars_in_expr = sorted(set(
            t for t in all_tokens
            if re.match(r'^[A-Z][A-Z0-9_]*$', t)
        ))
        self.current_vars = vars_in_expr
        n = len(self.current_vars)

        self.tree.delete(*self.tree.get_children())
        cols = self.current_vars + ['Wynik (Y)']
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100 if c == 'Wynik (Y)' else 60, anchor="center")
        self.truth_data = {}
        for i in range(2**n):
            val = i^(i>>1) if self.order_var.get() == "gray" else i
            bits = tuple((val>>(n-1-j))&1 for j in range(n))
            env = dict(zip(self.current_vars, bits))
            res = self.evaluate(proc, env)
            self.truth_data[bits] = res
            self.tree.insert('', 'end', values=list(bits) + [res])
        self._run_minimize_and_display()

    def _run_minimize_and_display(self):
        n = len(self.current_vars)
        if n == 0: self.lbl_min_func.config(text=""); self.optimal_cover=[]; return
        ones = [sum(b*(1<<(n-1-j)) for j,b in enumerate(bits))
                for bits,v in self.truth_data.items() if v==1]
        dcs = [sum(b*(1<<(n-1-j)) for j,b in enumerate(bits))
               for bits,v in self.truth_data.items() if v=='-']
        cover, text = minimize_from_minterms(ones, dcs, n, self.current_vars)
        self.optimal_cover = cover; self.lbl_min_func.config(text=text)

    def _rebuild_tree_from_truth_data(self):
        n = len(self.current_vars)
        self.tree.delete(*self.tree.get_children())
        cols = self.current_vars + ['Wynik (Y)']
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=100 if c == 'Wynik (Y)' else 60, anchor="center")
        for i in range(2**n):
            val = i^(i>>1) if self.order_var.get() == "gray" else i
            bits = tuple((val>>(n-1-j))&1 for j in range(n))
            v = self.truth_data.get(bits, 0)
            self.tree.insert('', 'end', values=list(bits) + [v])

    # ── copy markdown ─────────────────────────
    def btn_temp_text(self, btn):
        old = btn.cget("text"); btn.config(text="✅ Skopiowano")
        self.root.after(1500, lambda: btn.config(text=old))

    def copy_table_markdown(self):
        if not self.truth_data: return
        cols = self.tree["columns"]
        md = ["| " + " | ".join(cols) + " |", "|" + "| ".join(["---"]*len(cols)) + "|"]
        for item in self.tree.get_children():
            v = list(self.tree.item(item, "values"))
            if v[-1] == "1": v[-1] = "**1**"
            md.append("| " + " | ".join(map(str,v)) + " |")
        self.root.clipboard_clear(); self.root.clipboard_append("\n".join(md))
        self.btn_temp_text(self.btn_copy_md)


    # ══════════════════════════════════════════
    #  K-MAP WINDOW
    # ══════════════════════════════════════════
    def show_kmap(self):
        win=tk.Toplevel(self.root); win.title("Siatka Karnaugha")
        win.configure(bg=self.colors['bg']); self.set_window_icon(win)

        top_bar=tk.Frame(win,bg=self.colors['high']); top_bar.pack(fill=tk.X,padx=10,pady=(10,0))
        tk.Label(top_bar,text="Zmienne:",bg=self.colors['high'],fg=self.colors['txt'],
            font=('Consolas',10)).pack(side=tk.LEFT,padx=(8,4),pady=5)

        self._kmap_n_var=tk.IntVar()
        default_n = len(self.current_vars) if 2<=len(self.current_vars)<=5 else 4
        self._kmap_n_var.set(default_n)
        for nv in [2,3,4,5]:
            tk.Radiobutton(top_bar,text=str(nv),variable=self._kmap_n_var,value=nv,
                bg=self.colors['high'],fg=self.colors['txt'],selectcolor=self.colors['surf'],
                activebackground=self.colors['active'],activeforeground=self.colors['txt'],
                bd=0,highlightthickness=0,command=lambda:self._kmap_on_n_change(win)
            ).pack(side=tk.LEFT,padx=3,pady=5)

        self._kmap5_mode=tk.StringVar(value="single")
        self._kmap5_mode_frame=tk.Frame(top_bar,bg=self.colors['high'])
        tk.Label(self._kmap5_mode_frame,text="Tryb 5-var:",bg=self.colors['high'],
            fg=self.colors['txt'],font=('Consolas',9)).pack(side=tk.LEFT,padx=(0,4))
        for lbl,val in [("Jedna siatka","single"),("Dwie siatki","dual")]:
            tk.Radiobutton(self._kmap5_mode_frame,text=lbl,variable=self._kmap5_mode,value=val,
                bg=self.colors['high'],fg=self.colors['txt'],selectcolor=self.colors['surf'],
                activebackground=self.colors['active'],activeforeground=self.colors['txt'],
                bd=0,highlightthickness=0,command=self._kmap_render_dispatch
            ).pack(side=tk.LEFT,padx=3)

        self.kmap_canvas=tk.Canvas(win,bg=self.colors['surf'],highlightthickness=0)
        self.kmap_canvas.pack(expand=True,fill=tk.BOTH,padx=10,pady=(10,0))

        self._kmap_func_widget=tk.Text(win,height=1,font=('Consolas',11,'bold'),
            bg=self.colors['bg'],fg=self.colors['txt'],relief=tk.FLAT,bd=0,
            highlightthickness=0,state=tk.DISABLED,cursor="arrow",wrap=tk.NONE)
        self._kmap_func_widget.pack(fill=tk.X,padx=12,pady=(5,0))

        bot=tk.Frame(win,bg=self.colors['high']); bot.pack(fill=tk.X,padx=10,pady=(6,10))

        self.show_groups_var=tk.BooleanVar(value=True)
        tk.Checkbutton(bot,text="Pokaż grupy",variable=self.show_groups_var,
            command=self._full_refresh,
            bg=self.colors['high'],fg=self.colors['txt'],selectcolor=self.colors['surf'],
            activebackground=self.colors['active'],activeforeground=self.colors['txt'],
            bd=0,highlightthickness=0).pack(side=tk.LEFT,padx=10,pady=5)

        self.show_axes_var=tk.BooleanVar(value=False)
        self._axes_cb=tk.Checkbutton(bot,text="Osie symetrii",variable=self.show_axes_var,
            command=self._kmap_render_dispatch,
            bg=self.colors['high'],fg=self.colors['txt'],selectcolor=self.colors['surf'],
            activebackground=self.colors['active'],activeforeground=self.colors['txt'],
            bd=0,highlightthickness=0)

        btn_copy_kmap = ttk.Button(bot, text="Kopiuj MD")
        btn_copy_kmap.pack(side=tk.RIGHT, padx=10, pady=5)

        btn_clear_kmap = ttk.Button(bot, text="Wyczyść", command=self._kmap_clear)
        btn_clear_kmap.pack(side=tk.RIGHT, padx=5, pady=5)

        self._kmap_init_data(default_n)
        self._update_5var_ui(default_n)
        self.kmap_canvas.bind("<Configure>",lambda e:self._kmap_render_dispatch())
        btn_copy_kmap.config(command=lambda:self._kmap_copy_md(btn_copy_kmap))
        win.protocol("WM_DELETE_WINDOW",lambda:self._kmap_on_close(win))
        win.geometry("920x600" if default_n==5 else "520x580")

    # ── helpers ───────────────────────────────
    def _update_5var_ui(self, n):
        if n == 5:
            self._kmap5_mode_frame.pack(side=tk.RIGHT, padx=8)
            self._axes_cb.pack(side=tk.LEFT, padx=2, pady=5)
        else:
            self._kmap5_mode_frame.pack_forget()
            self._axes_cb.pack_forget()

    def _kmap_init_data(self, n):
        """
        Inicjalizacja danych siatki przy pierwszym otwarciu okna K-mapy.
        - n == m (dokładne dopasowanie): kopiuj truth_data bezpośrednio
        - n > m (siatka większa niż wyrażenie): rozszerz – bity wyrażenia
          mapują się do pierwszych m bitów każdej komórki siatki
        - n < m lub brak wyrażenia: zacznij od zera
        """
        self._kmap_n = n
        m = len(self.current_vars)

        if m == n and self.truth_data:
            self._kmap_vars = list(self.current_vars)
            self._kmap_data = dict(self.truth_data)
        elif 2 <= m < n and self.truth_data:
            # Siatka większa – rozszerz
            self._kmap_vars = (self.current_vars + self.ALPHABET)[:n]
            new_data = {}
            for i in range(2**n):
                bits = tuple((i >> (n - 1 - j)) & 1 for j in range(n))
                expr_bits = bits[:m]
                new_data[bits] = self.truth_data.get(expr_bits, 0)
            self._kmap_data = new_data
        else:
            # Brak wyrażenia lub za dużo zmiennych – zacznij od zera
            self._kmap_vars = self.ALPHABET[:n]
            self._kmap_data = {tuple((i>>(n-1-j))&1 for j in range(n)): 0 for i in range(2**n)}

        self._kmap_recompute()

    def _kmap_on_n_change(self, win):
        """
        Zmiana liczby zmiennych na siatce w trakcie pracy z K-mapą.
        - Jeśli nowy n >= m: pokaż ekwiwalentną funkcję (rozszerzenie)
        - Jeśli nowy n < m: wyczyść (za mało miejsca)
        """
        n = self._kmap_n_var.get()
        m = len(self.current_vars)

        if m > 0 and n >= m:
            self._kmap_vars = (self.current_vars + self.ALPHABET)[:n]
            new_data = {}
            for i in range(2**n):
                bits = tuple((i >> (n - 1 - j)) & 1 for j in range(n))
                expr_bits = bits[:m]
                new_data[bits] = self.truth_data.get(expr_bits, 0)
            self._kmap_data = new_data
        else:
            self._kmap_vars = self.ALPHABET[:n]
            self._kmap_data = {tuple((i>>(n-1-j))&1 for j in range(n)): 0 for i in range(2**n)}

        self._kmap_n = n
        self._kmap_recompute()
        self._update_5var_ui(n)
        win.geometry("920x600" if n == 5 else "520x580")
        self._full_refresh()

    def _kmap_recompute(self):
        n = self._kmap_n
        ones = [sum(b*(1<<(n-1-j)) for j,b in enumerate(bits))
                for bits, v in self._kmap_data.items() if v == 1]
        dcs = [sum(b*(1<<(n-1-j)) for j,b in enumerate(bits))
               for bits, v in self._kmap_data.items() if v == '-']
        self._kmap_cover, self._kmap_func_text = minimize_from_minterms(ones, dcs, n, self._kmap_vars)

    def _full_refresh(self):
        self._update_func_display()
        self._kmap_render_dispatch()

    def _kmap_clear(self):
        for k in self._kmap_data:
            self._kmap_data[k] = 0
        self._kmap_recompute()
        self._full_refresh()

    # ── colored SOP label ─────────────────────
    def _update_func_display(self):
        if not hasattr(self,'_kmap_func_widget'): return
        w=self._kmap_func_widget
        w.config(state=tk.NORMAL); w.delete('1.0',tk.END)
        for tag in w.tag_names(): w.tag_delete(tag)

        cover = self._kmap_cover; text = self._kmap_func_text
        show_colors = self.show_groups_var.get() and cover

        if not show_colors:
            w.insert(tk.END, text)
        else:
            w.insert(tk.END, "f = ")
            for i,term in enumerate((text[4:] if text.startswith("f = ") else text).split(" + ")):
                tag = f"t{i}"; color = self.group_colors[i%len(self.group_colors)]
                w.tag_configure(tag, foreground=color)
                if i>0: w.insert(tk.END, " + ")
                w.insert(tk.END, term, tag)
        w.config(state=tk.DISABLED)

    # ── dispatch ──────────────────────────────
    def _kmap_render_dispatch(self):
        n=self._kmap_n
        if n==5 and self._kmap5_mode.get()=="single":
            self._kmap_render5_single()
        elif n==5:
            self._kmap_render5_dual()
        else:
            self._kmap_render_standard(n)

    # ── variable editing ──────────────────────
    def _kmap_edit_vars(self):
        current = ", ".join(self._kmap_vars)
        res = simpledialog.askstring("Edycja zmiennych",
                                     f"Podaj {self._kmap_n} zmiennych po przecinku:",
                                     initialvalue=current, parent=self.kmap_canvas)
        if res:
            new_vars = [v.strip() for v in res.split(',')]
            if len(new_vars) == self._kmap_n and all(new_vars):
                self._kmap_vars = new_vars
                self._kmap_recompute()
                self._full_refresh()

    def _bind_edit_vars(self, canvas, item):
        canvas.tag_bind(item, "<Button-1>", lambda e: self._kmap_edit_vars())
        canvas.tag_bind(item, "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind(item, "<Leave>", lambda e: canvas.config(cursor=""))

    # ══════════════════════════════════════════
    #  Universal group drawer
    # ══════════════════════════════════════════
    def _draw_group_set(self, cover, r_seq, c_seq, off_x, off_y, cw, ch):
        canvas = self.kmap_canvas
        n = self._kmap_n; nr = len(r_seq); nc = len(c_seq)
        for idx, pi in enumerate(cover):
            color = self.group_colors[idx % len(self.group_colors)]
            covered_r = set(); covered_c = set()
            for r in range(nr):
                for col in range(nc):
                    mt = "".join(map(str, r_seq[r] + c_seq[col]))
                    if all(pi[k] == '-' or pi[k] == mt[k] for k in range(n)):
                        covered_r.add(r); covered_c.add(col)
            ins = (idx * 4 + 6)
            for rs, re in find_runs_circular(covered_r, nr):
                for cs, ce in find_runs_circular(covered_c, nc):
                    x1 = off_x + cs * cw + ins; y1 = off_y + rs * ch + ins
                    x2 = off_x + (ce + 1) * cw - ins; y2 = off_y + (re + 1) * ch - ins
                    canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=3)

    # ══════════════════════════════════════════
    #  2 / 3 / 4 variable render
    # ══════════════════════════════════════════
    def _kmap_render_standard(self,n):
        canvas=self.kmap_canvas; canvas.delete("all")
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if w<50 or h<50: return

        rb=n//2; cb=n-rb
        r_seq=gray_seq(rb); c_seq=gray_seq(cb)
        rvars=self._kmap_vars[:rb]; cvars=self._kmap_vars[rb:]
        off_x=w*0.18; off_y=h*0.18
        cw=(w-off_x)/len(c_seq); ch=(h-off_y)/len(r_seq)
        c=self.colors

        for i,rv in enumerate(r_seq):
            for j,cv in enumerate(c_seq):
                key=rv+cv; val=self._kmap_data.get(key,0)
                x1=off_x+j*cw; y1=off_y+i*ch
                is_ones = (val == 1)
                canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline=c['brd'],
                    fill=c['k1'] if is_ones else c['bg'])
                canvas.create_text(x1+cw/2,y1+ch/2,text=str(val),
                    fill=c['k1_fg'] if is_ones else c['txt'],
                    font=("Consolas",14,"bold" if val != 0 else "normal"))
                hit=canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline="",fill="")

                canvas.tag_bind(hit,"<Button-1>",lambda e,k=key:self._kmap_toggle(k))
                canvas.tag_bind(hit,"<Button-3>",lambda e,k=key:self._kmap_toggle_dc(k))
                canvas.tag_bind(hit,"<Button-2>",lambda e,k=key:self._kmap_toggle_dc(k))

        lbl_corner = canvas.create_text(off_x/2,off_y/2,text=f"{''.join(rvars)}\\{''.join(cvars)}",
            fill=c['txt'],font=("Consolas",10,"bold"))
        self._bind_edit_vars(canvas, lbl_corner)

        for j,cv in enumerate(c_seq):
            canvas.create_text(off_x+j*cw+cw/2,off_y/2,text="".join(map(str,cv)),
                fill=c['txt'],font=("Consolas",11,"bold"))
        for i,rv in enumerate(r_seq):
            canvas.create_text(off_x/2,off_y+i*ch+ch/2,text="".join(map(str,rv)),
                fill=c['txt'],font=("Consolas",11,"bold"))

        if self.show_groups_var.get():
            self._draw_group_set(self._kmap_cover,r_seq,c_seq,off_x,off_y,cw,ch)

    # ══════════════════════════════════════════
    #  5-VARIABLE — SINGLE GRID  4 rows × 8 cols
    # ══════════════════════════════════════════
    def _kmap_render5_single(self):
        canvas=self.kmap_canvas; canvas.delete("all")
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if w<80 or h<60: return

        r_seq=KMAP5_ROW_SEQ; c_seq=KMAP5_COL_SEQ; vs=self._kmap_vars; c=self.colors
        off_x=w*0.09; off_y=h*0.18
        cw=(w-off_x-8)/8; ch=(h-off_y-8)/4

        for i,rv in enumerate(r_seq):
            for j,cv in enumerate(c_seq):
                key=rv+cv; val=self._kmap_data.get(key,0)
                x1=off_x+j*cw; y1=off_y+i*ch
                is_ones = (val == 1)
                canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline=c['brd'],
                    fill=c['k1'] if is_ones else c['bg'])
                canvas.create_text(x1+cw/2,y1+ch/2,text=str(val),
                    fill=c['k1_fg'] if is_ones else c['txt'],
                    font=("Consolas",12,"bold" if val != 0 else "normal"))
                hit=canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline="",fill="")

                canvas.tag_bind(hit,"<Button-1>",lambda e,k=key:self._kmap_toggle(k))
                canvas.tag_bind(hit,"<Button-3>",lambda e,k=key:self._kmap_toggle_dc(k))
                canvas.tag_bind(hit,"<Button-2>",lambda e,k=key:self._kmap_toggle_dc(k))

        lbl_corner = canvas.create_text(off_x/2,off_y/2,text=f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}{vs[4]}",
            fill=c['txt'],font=("Consolas",9,"bold"))
        self._bind_edit_vars(canvas, lbl_corner)

        for j,cv in enumerate(c_seq):
            canvas.create_text(off_x+j*cw+cw/2,off_y*0.55,text="".join(map(str,cv)),
                fill=c['txt'],font=("Consolas",10,"bold"))
        for i,rv in enumerate(r_seq):
            canvas.create_text(off_x/2,off_y+i*ch+ch/2,text="".join(map(str,rv)),
                fill=c['txt'],font=("Consolas",10,"bold"))

        if self.show_axes_var.get():
            self._draw_axes_single5(off_x,off_y,cw,ch,w,h)
        if self.show_groups_var.get():
            self._draw_group_set(self._kmap_cover,r_seq,c_seq,off_x,off_y,cw,ch)

    def _draw_axes_single5(self,off_x,off_y,cw,ch,w,h):
        canvas=self.kmap_canvas; ax=self.colors['axis']; dash=(4,4)
        gr=off_x+8*cw; gb=off_y+4*ch
        bx=off_x-6
        for yy in [off_y,off_y+3*ch]:
            canvas.create_line(bx,yy,bx,yy+ch,fill=ax,width=2,dash=dash)
        canvas.create_line(bx-8,off_y+ch/2,bx,off_y+ch/2,fill=ax,width=2)
        canvas.create_line(bx-8,off_y+3.5*ch,bx,off_y+3.5*ch,fill=ax,width=2)
        canvas.create_line(bx-8,off_y+ch/2,bx-8,off_y+3.5*ch,fill=ax,width=2,dash=dash)
        canvas.create_text(bx-18,off_y+2*ch,text=self._kmap_vars[0],fill=ax,font=("Consolas",9,"bold"))
        for yy in [off_y+ch,off_y+3*ch]:
            canvas.create_line(gr+4,yy,gr+14,yy,fill=ax,width=2)
        canvas.create_text(gr+22,off_y+ch,text=self._kmap_vars[1],fill=ax,font=("Consolas",9,"bold"))
        cx=off_x+4*cw
        canvas.create_line(cx,off_y-14,cx,gb+4,fill=ax,width=2,dash=dash)
        canvas.create_text(cx,off_y-21,text=f"← {self._kmap_vars[2]} →",fill=ax,font=("Consolas",8,"bold"))
        for ex in [off_x,gr]:
            canvas.create_line(ex,off_y-8,ex,gb+8,fill=ax,width=1,dash=(2,5))
        canvas.create_text(off_x-2,gb+16,text="↕C",fill=ax,font=("Consolas",7))
        for xx in [off_x+2*cw,off_x+6*cw]:
            canvas.create_line(xx,gb+4,xx,gb+14,fill=ax,width=2)
            canvas.create_text(xx,gb+22,text=self._kmap_vars[3],fill=ax,font=("Consolas",9,"bold"))
        for j in range(1,8):
            canvas.create_line(off_x+j*cw,gb+18,off_x+j*cw,gb+26,fill=ax,width=1,dash=dash)
        canvas.create_text(off_x+4*cw,gb+36,text=f"←— {self._kmap_vars[4]} —→",
            fill=ax,font=("Consolas",8,"bold"))

    # ══════════════════════════════════════════
    #  5-VARIABLE — DUAL GRID
    # ══════════════════════════════════════════
    def _kmap_render5_dual(self):
        canvas=self.kmap_canvas; canvas.delete("all")
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if w<100 or h<80: return

        c=self.colors; vs=self._kmap_vars
        r_seq=[(0,0),(0,1),(1,1),(1,0)]; c_seq=[(0,0),(0,1),(1,1),(1,0)]
        mt=h*0.16; ml=w*0.08; gap=w*0.06
        gw=(w-ml*2-gap)/2; gh=h-mt-10
        cw=gw/4; ch=gh/4

        for e_val in [0,1]:
            gx=ml+e_val*(gw+gap)
            canvas.create_text(gx+gw/2,mt/2-12,text=f"{vs[4]}={e_val}",
                fill=c['txt'],font=("Consolas",10,"bold"))
            for j,cv in enumerate(c_seq):
                canvas.create_text(gx+j*cw+cw/2,mt*0.75,text="".join(map(str,cv)),
                    fill=c['txt'],font=("Consolas",10,"bold"))
            for i,rv in enumerate(r_seq):
                if e_val==0:
                    canvas.create_text(ml/2,mt+i*ch+ch/2,text="".join(map(str,rv)),
                        fill=c['txt'],font=("Consolas",10,"bold"))
                for j,cv in enumerate(c_seq):
                    key=rv+cv+(e_val,); val=self._kmap_data.get(key,0)
                    x1=gx+j*cw; y1=mt+i*ch
                    is_ones = (val == 1)
                    canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline=c['brd'],
                        fill=c['k1'] if is_ones else c['bg'])
                    canvas.create_text(x1+cw/2,y1+ch/2,text=str(val),
                        fill=c['k1_fg'] if is_ones else c['txt'],
                        font=("Consolas",13,"bold" if val != 0 else "normal"))
                    hit=canvas.create_rectangle(x1,y1,x1+cw,y1+ch,outline="",fill="")

                    canvas.tag_bind(hit,"<Button-1>",lambda e,k=key:self._kmap_toggle(k))
                    canvas.tag_bind(hit,"<Button-3>",lambda e,k=key:self._kmap_toggle_dc(k))
                    canvas.tag_bind(hit,"<Button-2>",lambda e,k=key:self._kmap_toggle_dc(k))

        lbl_corner = canvas.create_text(ml/2,mt/2,text=f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}",fill=c['txt'],font=("Consolas",9,"bold"))
        self._bind_edit_vars(canvas, lbl_corner)

        if self.show_groups_var.get():
            self._draw_dual5_groups(r_seq,c_seq,ml,mt,gap,gw,cw,ch)

    def _draw_dual5_groups(self,r_seq,c_seq,ml,mt,gap,gw,cw,ch):
        canvas=self.kmap_canvas; n=5
        for idx,pi in enumerate(self._kmap_cover):
            color=self.group_colors[idx%len(self.group_colors)]
            ins=(idx*3+5)
            for e_val in [0,1]:
                if pi[4] not in ('-',str(e_val)): continue
                gx=ml+e_val*(gw+gap)
                cr=set(); cc=set()
                for r in range(4):
                    for col in range(4):
                        mt_bits=r_seq[r]+c_seq[col]+(e_val,)
                        m="".join(map(str,mt_bits))
                        if all(pi[k]=='-' or pi[k]==m[k] for k in range(n)):
                            cr.add(r); cc.add(col)
                if not cr or not cc: continue
                for rs,re in find_runs_circular(cr,4):
                    for cs,ce in find_runs_circular(cc,4):
                        x1=gx+cs*cw+ins; y1=mt+rs*ch+ins
                        x2=gx+(ce+1)*cw-ins; y2=mt+(re+1)*ch-ins
                        canvas.create_rectangle(x1,y1,x2,y2,outline=color,width=3)

    # ── cell toggle ───────────────────────────
    def _kmap_toggle(self, key):
        v = self._kmap_data.get(key, 0)
        self._kmap_data[key] = 1 if v == 0 or v == '-' else 0
        self._kmap_recompute()
        self._full_refresh()

    def _kmap_toggle_dc(self, key):
        v = self._kmap_data.get(key, 0)
        self._kmap_data[key] = '-' if v != '-' else 0
        self._kmap_recompute()
        self._full_refresh()

    # ── close → sync main window ──────────────
    def _kmap_on_close(self, win):
        self.current_vars = list(self._kmap_vars)
        self.truth_data = dict(self._kmap_data)
        self.optimal_cover = list(self._kmap_cover)
        func = self._kmap_func_text
        self.lbl_min_func.config(text=func)
        self._rebuild_tree_from_truth_data()
        win.destroy()

    # ── copy markdown ─────────────────────────
    def _kmap_copy_md(self,btn):
        n=self._kmap_n; lines=[]
        if n==5:
            vs=self._kmap_vars
            if self._kmap5_mode.get()=="single":
                r_seq=KMAP5_ROW_SEQ; c_seq=KMAP5_COL_SEQ
                hdr=[f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}{vs[4]}"]+["".join(map(str,cv)) for cv in c_seq]
                lines+=["| "+" | ".join(hdr)+" |","|"+"---| "*len(hdr)]
                for rv in r_seq:
                    row=["".join(map(str,rv))]
                    for cv in c_seq:
                        v=self._kmap_data.get(rv+cv,0)
                        row.append("**1**" if v==1 else ("**-**" if v=='-' else "0"))
                    lines.append("| "+" | ".join(row)+" |")
            else:
                rs=[(0,0),(0,1),(1,1),(1,0)]; cs=[(0,0),(0,1),(1,1),(1,0)]
                for e in [0,1]:
                    lines.append(f"\n**{vs[4]}={e}**\n")
                    hdr=[f"{vs[0]}{vs[1]}\\{vs[2]}{vs[3]}"]+["".join(map(str,cv)) for cv in cs]
                    lines+=["| "+" | ".join(hdr)+" |","|"+"---| "*len(hdr)]
                    for rv in rs:
                        row=["".join(map(str,rv))]
                        for cv in cs:
                            v=self._kmap_data.get(rv+cv+(e,),0)
                            row.append("**1**" if v==1 else ("**-**" if v=='-' else "0"))
                        lines.append("| "+" | ".join(row)+" |")
        else:
            rb=n//2; cb=n-rb
            r_seq=gray_seq(rb); c_seq=gray_seq(cb)
            rv=self._kmap_vars[:rb]; cv=self._kmap_vars[rb:]
            corner=f"{''.join(rv)}\\{''.join(cv)}"
            hdr=[corner]+["".join(map(str,x)) for x in c_seq]
            lines+=["| "+" | ".join(hdr)+" |","|"+"---| "*len(hdr)]
            for rv in r_seq:
                row=["".join(map(str,rv))]
                for cv in c_seq:
                    v=self._kmap_data.get(rv+cv,0)
                    row.append("**1**" if v==1 else ("**-**" if v=='-' else "0"))
                lines.append("| "+" | ".join(row)+" |")
        self.root.clipboard_clear(); self.root.clipboard_append("\n".join(lines))
        self.btn_temp_text(btn)


if __name__=="__main__":
    root=tk.Tk(); app=TruthTableApp(root); root.mainloop()