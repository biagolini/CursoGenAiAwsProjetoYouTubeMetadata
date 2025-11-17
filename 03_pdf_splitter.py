try:
    import os
    import re
    from pathlib import Path
    from PyPDF2 import PdfReader
    import pikepdf
    import fitz  # PyMuPDF
    from PIL import Image
    import io
    import pandas as pd
    from dotenv import load_dotenv
except ModuleNotFoundError as e:
    print(f"Erro: {e}")
    print("\nCrie e ative o ambiente virtual:")
    print("  python3 -m venv .venv")
    print("  source .venv/bin/activate  # No Windows: .venv\\Scripts\\activate")
    print("\nDepois instale as dependências:")
    print("  pip3 install -r requirements.txt")
    exit(1)

# Carregar variáveis do .env
load_dotenv()

# Constantes do .env
INPUT_FOLDER = os.getenv('INPUT_FOLDER')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER')
DATA_FOLDER = os.getenv('DATA_FOLDER')
TABLE_NAME = os.getenv('PDF_SEGMENTS_TABLE')
MAX_FILE_SIZE_MB = float(os.getenv('PDF_MAX_FILE_SIZE_MB', 4.5))
MAX_PAGES = int(os.getenv('PDF_MAX_PAGES', 100))
MAX_DEPTH = int(os.getenv('PDF_MAX_DEPTH', 3))
REMOVE_IMAGES = os.getenv('PDF_REMOVE_IMAGES', 'True').lower() == 'true'

# Validar MAX_DEPTH
if MAX_DEPTH is None:
    MAX_DEPTH = 3

# Criar pasta de output
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_sections_at_level(outline, level, reader):
    """Extrai seções de um nível específico do outline"""
    sections = []
    
    def traverse(items, current_level=0):
        for item in items:
            if isinstance(item, list):
                traverse(item, current_level + 1)
            else:
                if current_level == level:
                    page_num = reader.get_destination_page_number(item)
                    sections.append((item.title, page_num))
    
    traverse(outline)
    return sections

def compress_pdf_images(input_file):
    """Substitui imagens do PDF por quadrados pretos para reduzir tamanho"""
    if not REMOVE_IMAGES:
        return
    
    doc = fitz.open(input_file)
    
    # Verificar se o PDF tem páginas
    if doc.page_count == 0:
        doc.close()
        return
    
    # Processar cada página
    for page_num in range(doc.page_count):
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            try:
                # Extrair informações da imagem
                base_image = doc.extract_image(xref)
                width = base_image.get("width", 100)
                height = base_image.get("height", 100)
                
                # Criar imagem preta do mesmo tamanho
                black_image = Image.new('RGB', (width, height), color='black')
                
                # Salvar como JPEG comprimido
                output_buffer = io.BytesIO()
                black_image.save(output_buffer, format='JPEG', quality=10)
                black_bytes = output_buffer.getvalue()
                
                # Substituir imagem no PDF
                doc.update_stream(xref, black_bytes)
            except Exception:
                # Se falhar, manter imagem original
                continue
    
    temp_file = input_file + ".tmp"
    doc.save(temp_file, garbage=4, deflate=True, clean=True)
    doc.close()
    
    os.replace(temp_file, input_file)

def split_section(pdf, reader, start_page, end_page, output_dir, base_name, prefix, level, csv_data, original_pdf_name):
    """Divide uma seção recursivamente se necessário"""
    
    # Criar PDF temporário para verificar tamanho
    temp_pdf = pikepdf.new()
    temp_pdf.pages.extend(pdf.pages[start_page:end_page])
    
    num_pages = end_page - start_page
    temp_file = os.path.join(output_dir, f"temp_{prefix}.pdf")
    temp_pdf.remove_unreferenced_resources()
    temp_pdf.save(temp_file)
    temp_pdf.close()
    
    # Remover imagens antes de calcular tamanho
    compress_pdf_images(temp_file)
    
    file_size_mb = os.path.getsize(temp_file) / (1024*1024)
    
    # Verificar se respeita os limites
    exceeds_size = MAX_FILE_SIZE_MB and file_size_mb > MAX_FILE_SIZE_MB
    exceeds_pages = MAX_PAGES and num_pages > MAX_PAGES
    
    if not exceeds_size and not exceeds_pages:
        # Renomear arquivo temporário para final (já com imagens removidas)
        final_file = os.path.join(output_dir, f"{prefix}_{base_name}.pdf")
        os.rename(temp_file, final_file)
        
        # Adicionar ao DataFrame
        segment_name = f"{prefix}_{base_name}"
        relative_path = os.path.relpath(final_file, '.')
        csv_data.append({
            "original_pdf": original_pdf_name,
            "segment_name": segment_name,
            "segment_path": relative_path
        })
        
        # Recalcular tamanho após compressão
        file_size_mb = os.path.getsize(final_file) / (1024*1024)
        print(f"[OK] {prefix}: {num_pages} páginas ({file_size_mb:.2f} MB)")
        return [final_file]
    
    # Remove arquivo temporário
    os.remove(temp_file)
    
    # Se excede limites e ainda pode ir mais fundo
    if level < MAX_DEPTH:
        print(f"[AVISO] {prefix} excede limites ({num_pages} páginas, {file_size_mb:.2f} MB) - dividindo em subnível {level+1}")
        
        # Buscar subseções no próximo nível
        subsections = get_sections_at_level(reader.outline, level, reader)
        
        # Filtrar apenas subseções dentro do intervalo atual
        relevant_subsections = [(title, page) for title, page in subsections 
                                if start_page <= page < end_page]
        
        if len(relevant_subsections) > 1:
            # Adicionar marcador final
            relevant_subsections.append(("END", end_page))
            
            generated_files = []
            for i, (title, sub_start) in enumerate(relevant_subsections[:-1]):
                sub_end = relevant_subsections[i + 1][1]
                sub_prefix = f"{prefix}.{i+1:02d}"
                
                files = split_section(pdf, reader, sub_start, sub_end, 
                                     output_dir, base_name, sub_prefix, level + 1, csv_data, original_pdf_name)
                generated_files.extend(files)
            
            return generated_files
    
    # Se não pode dividir mais ou não há subseções, salva mesmo excedendo
    final_file = os.path.join(output_dir, f"{prefix}_{base_name}.pdf")
    final_pdf = pikepdf.new()
    final_pdf.pages.extend(pdf.pages[start_page:end_page])
    final_pdf.remove_unreferenced_resources()
    final_pdf.save(final_file)
    final_pdf.close()
    
    # Comprimir imagens
    compress_pdf_images(final_file)
    
    # Adicionar ao DataFrame
    segment_name = f"{prefix}_{base_name}"
    relative_path = os.path.relpath(final_file, '.')
    csv_data.append({
        "original_pdf": original_pdf_name,
        "segment_name": segment_name,
        "segment_path": relative_path
    })
    
    # Recalcular tamanho após compressão
    file_size_mb = os.path.getsize(final_file) / (1024*1024)
    print(f"[OK] {prefix}: {num_pages} páginas ({file_size_mb:.2f} MB) [LIMITE EXCEDIDO]")
    return [final_file]

# Coletar arquivos PDF
pdf_files = [f for f in os.listdir(INPUT_FOLDER) if f.lower().endswith('.pdf')]

print(f"Encontrados {len(pdf_files)} arquivos PDF para processar\n")

# Preparar lista para DataFrame
csv_data = []

# Processar cada PDF
for pdf_filename in sorted(pdf_files):
    pdf_path = os.path.join(INPUT_FOLDER, pdf_filename)
    base_name = Path(pdf_filename).stem
    
    # Limpar nome do arquivo para criar pasta
    folder_name = re.sub(r'\s+', '-', base_name)
    folder_name = re.sub(r'-+', '-', folder_name).strip('-')
    
    # Criar pasta específica para este PDF (limpar se já existir)
    output_dir = os.path.join(OUTPUT_FOLDER, folder_name)
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, file))
    else:
        os.makedirs(output_dir)
    
    print(f"Processando {pdf_filename}...")
    
    # Tamanho do arquivo original
    original_size = os.path.getsize(pdf_path)
    print(f"Tamanho original: {original_size / (1024*1024):.2f} MB")
    
    # Ler bookmarks com PyPDF2
    reader = PdfReader(pdf_path)
    
    # Verificar se há bookmarks (capítulos)
    if not reader.outline:
        print(f"Sem bookmarks encontrados. Use o arquivo original.\n")
        continue
    
    # Extrair bookmarks de nível 0 (capítulos principais)
    sections = get_sections_at_level(reader.outline, 0, reader)
    
    if not sections:
        print(f"Sem capítulos válidos encontrados. Use o arquivo original.\n")
        continue
    
    # Adicionar marcador final
    sections.append(("END", len(reader.pages)))
    
    # Abrir com pikepdf para dividir
    pdf = pikepdf.open(pdf_path)
    
    # Dividir PDF por capítulos
    all_files = []
    for i, (title, start_page) in enumerate(sections[:-1]):
        end_page = sections[i + 1][1]
        prefix = f"{i+1:02d}"
        
        files = split_section(pdf, reader, start_page, end_page, 
                             output_dir, folder_name, prefix, 1, csv_data, pdf_filename)
        all_files.extend(files)
    
    pdf.close()
    
    # Calcular tamanho total da pasta de saída
    total_size = sum(os.path.getsize(f) for f in all_files)
    print(f"Tamanho total da saída: {total_size / (1024*1024):.2f} MB")
    print(f"[OK] {pdf_filename} processado\n")

# Salvar DataFrame como CSV
os.makedirs(DATA_FOLDER, exist_ok=True)
csv_path = os.path.join(DATA_FOLDER, TABLE_NAME)

df = pd.DataFrame(csv_data)
df.to_csv(csv_path, index=False)

print("=== Processamento concluído ===")
print(f"CSV salvo em: {csv_path}")
print(f"Total de segmentos: {len(df)}")
