import tkinter as tk
from tkinter import messagebox

def add():
    try:
        num1 = float(entry1.get())
        num2 = float(entry2.get())
        result = num1 + num2
        result_var.set(result)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers")

def subtract():
    try:
        num1 = float(entry1.get())
        num2 = float(entry2.get())
        result = num1 - num2
        result_var.set(result)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers")

def multiply():
    try:
        num1 = float(entry1.get())
        num2 = float(entry2.get())
        result = num1 * num2
        result_var.set(result)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers")

def divide():
    try:
        num1 = float(entry1.get())
        num2 = float(entry2.get())
        if num2 == 0:
            messagebox.showerror("Math Error", "Division by zero is not allowed")
            result_var.set("Error")
        else:
            result = num1 / num2
            result_var.set(result)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numbers")

# Create the main window
root = tk.Tk()
root.title("Simple Calculator")

# Create and place widgets
tk.Label(root, text="Number 1:").grid(row=0, column=0, padx=10, pady=10)
tk.Label(root, text="Number 2:").grid(row=1, column=0, padx=10, pady=10)

entry1 = tk.Entry(root)
entry2 = tk.Entry(root)
entry1.grid(row=0, column=1, padx=10, pady=10)
entry2.grid(row=1, column=1, padx=10, pady=10)

tk.Button(root, text="Add", command=add).grid(row=2, column=0, padx=10, pady=10)
tk.Button(root, text="Subtract", command=subtract).grid(row=2, column=1, padx=10, pady=10)
tk.Button(root, text="Multiply", command=multiply).grid(row=3, column=0, padx=10, pady=10)
tk.Button(root, text="Divide", command=divide).grid(row=3, column=1, padx=10, pady=10)

result_var = tk.StringVar()
tk.Label(root, text="Result:").grid(row=4, column=0, padx=10, pady=10)
tk.Label(root, textvariable=result_var).grid(row=4, column=1, padx=10, pady=10)

# Run the application
root.mainloop()
