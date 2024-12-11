import os

# 폴더에서 PDF 파일명 리스트 가져오기
def get_pdf_filenames(directory):
    if not os.path.exists(directory):
        print(f"Directory does not exist: {directory}")
        return []
    return [file for file in os.listdir(directory) if file.endswith(".pdf")]

# 두 리스트 비교하여 첫 번째 리스트에만 있는 파일 출력
def compare_pdf_lists(pdf1, pdf2):
    missing_files = [file for file in pdf1 if file not in pdf2]
    if missing_files:
        print("Files in PDF1 but not in PDF2:")
        for file in missing_files:
            print(f"- {file}")
    else:
        print("All files in PDF1 are present in PDF2.")

# 메인 코드
if __name__ == "__main__":
    pdf1_directory = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/PDF"
    pdf2_directory = "/Users/skan/Desktop/AI_Prototyping_Team/MS_Azure_RAG/PDF2"
    
    pdf1 = get_pdf_filenames(pdf1_directory)
    pdf2 = get_pdf_filenames(pdf2_directory)
    
    compare_pdf_lists(pdf1, pdf2)
