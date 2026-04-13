from fpdf import FPDF

def remove_emojis(text):
    return text.encode('ascii', 'ignore').decode('ascii')

def generer_pdf(matiere: str, sujet: str, mode: str, messages: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 14, remove_emojis("Fiche de révision - Classe de 5ème"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, remove_emojis(f"Matière : {matiere}  |  Sujet : {sujet}  |  Mode : {mode}"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, remove_emojis("Contenu de la séance :"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 11)
    
    for msg in messages:
        if msg["role"] == "assistant":
            clean_text = remove_emojis(msg["content"])
            pdf.multi_cell(0, 7, clean_text)
            pdf.ln(3)
    return bytes(pdf.output())
