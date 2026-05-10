import tkinter as tk

def main():
    root = tk.Tk()
    root.title("UiTestAuto Dummy App")
    root.geometry("300x200")

    widgets = {}

    # --- Title ---
    lbl_title = tk.Label(root, text="Test Automation Target", name="lbl_title")
    lbl_title.pack(anchor="w", padx=10, pady=5)
    widgets["lbl_title"] = lbl_title

    # --- Form ---
    form_frame = tk.Frame(root)
    form_frame.pack(fill="x", padx=10, pady=5)

    lbl_name = tk.Label(form_frame, text="Name:")
    lbl_name.pack(side="left")

    entry_name = tk.Entry(form_frame, name="name_entry")
    entry_name.pack(side="left", fill="x", expand=True, padx=5)
    widgets["name_entry"] = entry_name

    # --- Buttons ---
    btn_frame = tk.Frame(root)
    btn_frame.pack(padx=10, pady=5)

    btn_click_me = tk.Button(btn_frame, text="Click Me", name="click_btn")
    btn_click_me.pack(side="left", padx=5)
    widgets["click_btn"] = btn_click_me

    btn_submit = tk.Button(btn_frame, text="Submit", name="submit_btn")
    btn_submit.pack(side="left", padx=5)
    widgets["submit_btn"] = btn_submit

    # --- Status ---
    lbl_status = tk.Label(root, text="Waiting...", name="status_lbl")
    lbl_status.pack(anchor="w", padx=10, pady=5)
    widgets["status_lbl"] = lbl_status

    # --- Handlers ---
    def on_click():
        lbl_status.config(text="Button Clicked!")

    def on_submit():
        lbl_status.config(text=f"Submitted: {entry_name.get()}")

    btn_click_me.config(command=on_click)
    btn_submit.config(command=on_submit)

    root.mainloop()


if __name__ == "__main__":
    main()