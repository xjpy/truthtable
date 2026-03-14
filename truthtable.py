import tkinter as tk
from tkinter import ttk, messagebox
import re

class TruthTableApp:
    def __init__(self, root):
        self.root = root
        self.root.title("")
        self.root.geometry("600x450")
        # icon = tk.PhotoImage(file='binary.png')
        # self.root.iconphoto(True, icon)
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        self.truth_data = {}
        self.current_vars = []
        
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sekcja wprowadzania danych
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Wyrażenie:", font=('', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        self.entry_expr = ttk.Entry(input_frame, font=('Consolas', 12))
        self.entry_expr.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.entry_expr.bind('<Return>', lambda e: self.generate())
        
        btn_gen = ttk.Button(input_frame, text="Generuj", command=self.generate)
        btn_gen.pack(side=tk.LEFT)

        # Sekcja opcji
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(options_frame, text="Kolejność:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.order_var = tk.StringVar(value="binary")
        ttk.Radiobutton(options_frame, text="Binarna", variable=self.order_var, value="binary", command=self.generate).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(options_frame, text="Kod Graya", variable=self.order_var, value="gray", command=self.generate).pack(side=tk.LEFT, padx=(0, 20))

        btn_kmap = ttk.Button(options_frame, text="Siatka Karnaugha", command=self.show_kmap)
        btn_kmap.pack(side=tk.RIGHT)

        # Sekcja tabeli (Treeview)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(table_frame, show='headings', yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.tree.yview)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def preprocess_expression(self, expr):
        expr = re.sub(r'(?i)\bXNOR\b', '#', expr)
        expr = re.sub(r'(?i)\bXOR\b', '^', expr)
        expr = re.sub(r'(?i)\bAND\b', '*', expr)
        expr = re.sub(r'(?i)\bOR\b', '+', expr)
        expr = re.sub(r'(?i)\bNOT\b', '!', expr)
        expr = expr.replace(' ', '')
        
        changed = True
        while changed:
            old_expr = expr
            expr = re.sub(r'([A-Za-z01])([A-Za-z01])', r'\1*\2', expr)
            expr = re.sub(r'([A-Za-z01])\(', r'\1*(', expr)
            expr = re.sub(r'\)([A-Za-z01])', r')*\1', expr)
            expr = re.sub(r'\)\(', r')*(', expr)
            expr = re.sub(r'([A-Za-z01])!', r'\1*!', expr)
            expr = re.sub(r'\)!', r')*!', expr)
            if old_expr == expr:
                changed = False
        return expr

    def evaluate(self, expr, env):
        precedence = {'!': 4, '*': 3, '^': 2, '#': 2, '+': 1, '(': 0}
        output, operators = [], []

        for token in expr:
            if token.isalpha(): output.append(env[token])
            elif token in '01': output.append(int(token))
            elif token == '(': operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    output.append(operators.pop())
                if operators: operators.pop()
                else: raise ValueError("Niezgodność nawiasów!")
            elif token in precedence:
                while (operators and operators[-1] != '(' and 
                       precedence.get(operators[-1], 0) >= precedence[token] and token != '!'):
                    output.append(operators.pop())
                operators.append(token)
            else:
                raise ValueError(f"Nieznany znak: {token}")

        while operators:
            op = operators.pop()
            if op == '(': raise ValueError("Niezgodność nawiasów!")
            output.append(op)

        stack = []
        for token in output:
            if isinstance(token, int): stack.append(token)
            elif token == '!':
                if not stack: raise ValueError("Błąd składni: '!'")
                stack.append(1 - stack.pop())
            elif token in '*+^#':
                if len(stack) < 2: raise ValueError(f"Błąd składni: '{token}'")
                b = stack.pop()
                a = stack.pop()
                if token == '*': stack.append(a & b)
                elif token == '+': stack.append(a | b)
                elif token == '^': stack.append(a ^ b)
                elif token == '#': stack.append(1 - (a ^ b))

        if len(stack) != 1: raise ValueError("Błąd wyrażenia.")
        return stack[0]

    def generate(self):
        raw_expr = self.entry_expr.get().strip()
        if not raw_expr: return

        try:
            processed_expr = self.preprocess_expression(raw_expr)
            self.current_vars = sorted(list(set(re.findall(r'[A-Za-z]', processed_expr))))
            n_vars = len(self.current_vars)
            
            if n_vars > 12:
                messagebox.showwarning("Uwaga", "Maksymalnie 12 zmiennych.")
                return

            self.tree.delete(*self.tree.get_children())
            columns = self.current_vars + ['Wynik (Y)']
            self.tree["columns"] = columns

            for col in columns:
                self.tree.heading(col, text=col)
                width = 100 if col == 'Wynik (Y)' else 60
                self.tree.column(col, anchor=tk.CENTER, width=width, stretch=tk.NO if col != 'Wynik (Y)' else tk.YES)

            self.truth_data.clear()
            use_gray = (self.order_var.get() == "gray")

            for i in range(2**n_vars):
                if use_gray:
                    # Konwersja indeksu binarnego na kod Graya
                    val = i ^ (i >> 1)
                else:
                    val = i
                
                # Tworzenie krotki z wartościami bitów
                combination = tuple((val >> (n_vars - 1 - j)) & 1 for j in range(n_vars))
                
                env = dict(zip(self.current_vars, combination))
                result = self.evaluate(processed_expr, env)
                self.truth_data[combination] = result
                
                self.tree.insert('', tk.END, values=list(combination) + [result])

        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def show_kmap(self):
        if not self.truth_data:
            messagebox.showinfo("Brak danych", "Najpierw wygeneruj tablicę prawdy.")
            return
            
        n_vars = len(self.current_vars)
        if n_vars not in [2, 3, 4]:
            messagebox.showwarning("Siatka Karnaugha", "Siatka Karnaugha obsługuje wyłącznie 2, 3 lub 4 zmienne.")
            return

        kmap_win = tk.Toplevel(self.root)
        kmap_win.title("Siatka Karnaugha")
        kmap_win.geometry("450x350")
        kmap_win.grab_set()

        # Konfiguracja osi siatki w zależności od ilości zmiennych
        if n_vars == 2:
            row_vars, col_vars = self.current_vars[0:1], self.current_vars[1:2]
        elif n_vars == 3:
            row_vars, col_vars = self.current_vars[0:1], self.current_vars[1:3]
        else: # 4 zmienne
            row_vars, col_vars = self.current_vars[0:2], self.current_vars[2:4]
            
        def get_gray_sequence(n):
            if n == 1: return [(0,), (1,)]
            return [(0,0), (0,1), (1,1), (1,0)]
            
        row_seq = get_gray_sequence(len(row_vars))
        col_seq = get_gray_sequence(len(col_vars))

        frame = ttk.Frame(kmap_win, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)

        # Komórka lewy-górny róg (oznaczenia osi)
        corner_text = f"{''.join(row_vars)} \\ {''.join(col_vars)}"
        ttk.Label(frame, text=corner_text, font=('Consolas', 11, 'bold'), borderwidth=1, relief="solid", padding=8, anchor=tk.CENTER).grid(row=0, column=0, sticky="nsew")

        # Nagłówki kolumn
        for c, col_val in enumerate(col_seq):
            label = "".join(map(str, col_val))
            ttk.Label(frame, text=label, font=('Consolas', 11, 'bold'), borderwidth=1, relief="solid", padding=8, anchor=tk.CENTER, background="#e0e0e0").grid(row=0, column=c+1, sticky="nsew")

        # Wiersze z danymi
        for r, row_val in enumerate(row_seq):
            # Nagłówek wiersza
            label = "".join(map(str, row_val))
            ttk.Label(frame, text=label, font=('Consolas', 11, 'bold'), borderwidth=1, relief="solid", padding=8, anchor=tk.CENTER, background="#e0e0e0").grid(row=r+1, column=0, sticky="nsew")
            
            # Wartości w siatce
            for c, col_val in enumerate(col_seq):
                full_key = row_val + col_val
                val = self.truth_data.get(full_key, 0)
                
                # Podświetl jedynki w siatce by poprawić czytelność
                bg_color = "#c8e6c9" if val == 1 else "#ffffff"
                
                ttk.Label(frame, text=str(val), font=('Consolas', 12), borderwidth=1, relief="solid", padding=8, anchor=tk.CENTER, background=bg_color).grid(row=r+1, column=c+1, sticky="nsew")

        # Równomierne rozciąganie komórek
        for i in range(len(col_seq) + 1):
            frame.columnconfigure(i, weight=1)
        for i in range(len(row_seq) + 1):
            frame.rowconfigure(i, weight=1)

if __name__ == "__main__":
    root = tk.Tk()
    app = TruthTableApp(root)
    root.mainloop()