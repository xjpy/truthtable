# TRUTHTABLE: Truth Table & K-Map Generator

A lightweight Python desktop application for generating truth tables and minimizing Boolean functions using the Quine-McCluskey algorithm. The tool visualizes Karnaugh Maps (K-Maps) and identifies optimal groupings for 2 to 4 variables.

> **Note:** The current user interface is in **Polish**, but the core logic and expressions follow international Boolean algebra standards.

## Features
* **Truth Table Engine**: Supports `AND`, `OR`, `NOT`, `XOR`, `XNOR` with flexible syntax (words or symbols).
* **Function Minimization**: Automatically calculates the simplest Sum of Products (SOP) form.
* **Interactive K-Maps**: Dynamic rendering of Karnaugh Maps with a toggle to show/hide prime implicant groups.
* **Binary/Gray Code**: Toggle between standard binary and Gray code ordering for the truth table.
* **Markdown Export**: One-click "Copy to MD" buttons for both tables and K-maps (perfect for documentation).
* **Theme Support**: Dynamic Dark/Light mode switching (Hotcheck: `F12`).

## Expression Syntax
The parser handles various notation styles:
* `A B + !C`
* `A AND B OR NOT C`
* `A * B + !C`
* `(A ^ B) # (C + D)`

## Requirements
* **Python 3.x**
* **Tkinter** (Standard Library)
* No external dependencies required.

## Installation & Usage
1. Download `truthtable.py`.
2. (Optional) Place an `icon.png` in the same directory for a custom window icon.

 
*To launch the application without the background terminal window (stealth mode), run via the provided `run.vbs` script.*
