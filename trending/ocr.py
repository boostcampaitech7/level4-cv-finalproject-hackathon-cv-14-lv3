import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일에서 환경변수 로드
load_dotenv()

# Supabase 설정
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def is_image_file(filename):
    valid_extensions = ('.jpg', '.jpeg', '.png')
    return filename.lower().endswith(valid_extensions)

def extract_category(line):
    """'인기검색어' 패턴이 있는 줄에서 카테고리 추출"""
    if '인기검색어' in line:
        category = line.split('인기검색어')[0].strip()
        print(f"카테고리: {category}")
        return category
    return None

def extract_date_range(line):
    """날짜 범위 추출"""
    if '클릭량 추이' in line and '2025.' in line and '~' in line:
        try:
            # 날짜 부분만 추출
            dates = line.split('~')
            start = dates[0].split('2025.')[1].strip().strip('.')
            start_date = f"2025-{start.replace('.', '-')}"
            
            # 끝 날짜 추출 시 불필요한 텍스트 제거
            end_part = dates[1].split('2025.')[1]
            end = end_part.split()[0].strip().strip('.') 
            end_date = f"2025-{end.replace('.', '-')}"
            
            print(f"날짜 범위: {start_date} ~ {end_date}")
            return start_date, end_date
        except Exception as e:
            print(f"날짜 추출 중 에러: {str(e)}")
            return None, None
    return None, None

def extract_data(ocr_result):
    """OCR 결과에서 카테고리와 순위 정보 추출"""
    text = ocr_result['pages'][0]['text']
    lines = text.split('\n')
    rankings = []        # 검색량 순위
    category = None      # 상품 카테고리
    start_date = None    # 조회기간 시작일
    end_date = None      # 조회기간 종료일
    valid_products = {}
    
    print("\n=== 데이터 추출 시작 ===")
    
    # 카테고리, 날짜 추출
    for line in lines:
        if not category and '인기검색어' in line:
            category = extract_category(line)
        
        if not start_date and '클릭량 추이' in line:
            start_date, end_date = extract_date_range(line)
        
        if category and start_date and end_date:
            break
    
    if not all([category, start_date, end_date]):
        print(f"필수 정보 누락: 카테고리={category}, 시작일={start_date}, 종료일={end_date}")
        return []

    print("\n=== 순위 데이터 추출 시작 ===")
    for line in lines:
        words = line.strip().split()
        for i in range(len(words)-1):
            if words[i].isdigit():
                rank = int(words[i])
                if 1 <= rank <= 5:
                    product_name = words[i+1].strip()
                    
                    # 잘못된 추출정보 필터링
                    if (product_name == 'V' or product_name.isdigit()):
                        continue
                    
                    # 순위별로 저장
                    if rank not in valid_products or len(product_name) > len(valid_products[rank]):
                        valid_products[rank] = product_name
                        print(f"Rank - Product: {rank}위 - {product_name}")
    
    rankings = [
        {
            "category": category,
            "rank": rank,
            "product_name": product_name,
            "start_date": start_date,
            "end_date": end_date
        }
        for rank, product_name in valid_products.items()
    ]
    
    rankings = sorted(rankings, key=lambda x: x['rank'])
    return rankings

def save_to_supabase(rankings):
    """Supabase에 데이터 저장"""
    try:
        if rankings:
            rankings = sorted(rankings, key=lambda x: x['rank'])
            category = rankings[0]['category']
            start_date = rankings[0]['start_date']
            
            print(f"\n=== Database 저장 ===")
            
            # 기존 데이터 삭제
            supabase.table('trend_product')\
                    .delete()\
                    .eq('category', category)\
                    .eq('start_date', start_date)\
                    .execute()
            print("기존 데이터 삭제 완료")
            
            # 데이터 추가
            result = supabase.table('trend_product').insert(rankings).execute()
            print(f"{len(rankings)}개 데이터 저장 완료")
            return result
    except Exception as e:
        print(f"데이터 저장 중 에러: {str(e)}")
        return None

def ocr_image(image_path):
    """이미지 OCR 처리"""
    api_key = os.getenv('UPSTAGE_API_KEY')
    url = os.getenv('UPSTAGE_OCR_URL')
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print(f"\n=== OCR 요청 시작: {image_path} ===")
    
    try:
        with open(image_path, "rb") as image_file:
            files = {"document": image_file}
            response = requests.post(url, headers=headers, files=files)
            
        print(f"OCR 응답 상태 코드: {response.status_code}")
        if response.status_code != 200:
            print(f"OCR 에러 응답: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"OCR 처리 중 에러: {str(e)}")
        return None

def process_directory(directory_path):
    """Image Directory 내 이미지 처리"""
    print(f"\n=== Image Directory 처리 시작: {directory_path} ===")
    
    for filename in os.listdir(directory_path):
        if is_image_file(filename):
            image_path = os.path.join(directory_path, filename)
            print(f"\n처리 중인 파일: {filename}")
            
            result = ocr_image(image_path)
            if result:
                rankings = extract_data(result)
                if rankings:
                    save_to_supabase(rankings)
                else:
                    print("추출된 순위 데이터가 없습니다.")
            else:
                print("OCR 처리 실패")

if __name__ == "__main__":
    output_dir = "크롤링된 image dir 경로"
    process_directory(output_dir)