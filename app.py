import streamlit as st
from PIL import Image, ImageChops
import io
import zipfile
import math

def get_content_bbox(img):
    """이미지 내에서 실제 제품의 경계 상자를 찾는 함수"""
    if img.mode != 'RGBA':
        img = img.convert("RGBA")
    
    bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    
    if not bbox:
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        
    return bbox

def get_area_ratio(img):
    """레퍼런스 이미지에서 제품이 차지하는 '면적(Area) 비율'을 계산"""
    bbox = get_content_bbox(img)
    if not bbox:
        return 0.5 # 기본값
        
    product_w = bbox[2] - bbox[0]
    product_h = bbox[3] - bbox[1]
    product_area = product_w * product_h
    canvas_area = img.width * img.height
    
    return product_area / canvas_area

def resize_by_area(img, target_size, target_area_ratio):
    """면적 비율을 유지하며 고화질 리사이징 및 중앙 배치"""
    bbox = get_content_bbox(img)
    if not bbox:
        return img.convert("RGB").resize(target_size, Image.LANCZOS)
    
    product = img.crop(bbox)
    orig_w, orig_h = product.size
    
    target_canvas_area = target_size[0] * target_size[1]
    target_product_area = target_canvas_area * target_area_ratio
    
    # 목표 면적을 맞추기 위한 확대/축소 스케일 계산
    scale = math.sqrt(target_product_area / (orig_w * orig_h))
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    
    # 예외 처리: 얇고 긴 제품이 캔버스 밖으로 삐져나가는 것을 방지 (5% 여백 강제 확보)
    if new_w > target_size[0] * 0.95 or new_h > target_size[1] * 0.95:
        scale = min((target_size[0] * 0.95) / orig_w, (target_size[1] * 0.95) / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        
    # 화질 저하 방지를 위해 LANCZOS 필터 적용 (가장 정교한 안티앨리어싱)
    product = product.resize((new_w, new_h), Image.LANCZOS)
    
    new_canvas = Image.new("RGB", target_size, (255, 255, 255))
    
    # 정확한 중앙 정렬
    x_offset = (target_size[0] - new_w) // 2
    y_offset = (target_size[1] - new_h) // 2
    
    new_canvas.paste(product, (x_offset, y_offset), product if product.mode == 'RGBA' else None)
    return new_canvas

# --- UI 설정 ---
st.set_page_config(page_title="MD Image Optimizer", layout="wide")
st.title("📐 제품컷 면적 비례 & 고화질 리사이징 도구")
st.markdown("제품의 형태(가로/세로)가 달라도 **레퍼런스와 동일한 시각적 볼륨감(면적)**으로 자동 보정합니다.")

# 사이드바: 출력 사이즈 지정
st.sidebar.header("1. 출력 사이즈 설정 (px)")
out_width = st.sidebar.number_input("가로 폭 (Width)", value=1000, step=100)
out_height = st.sidebar.number_input("세로 높이 (Height)", value=1000, step=100)
target_size = (out_width, out_height)

st.sidebar.divider()

st.sidebar.header("2. 레퍼런스 설정")
ref_file = st.sidebar.file_uploader("면적 기준이 될 레퍼런스 이미지", type=['jpg', 'png', 'jpeg'])

if ref_file:
    ref_img = Image.open(ref_file)
    area_ratio = get_area_ratio(ref_img)
    st.sidebar.image(ref_img, caption=f"학습 완료: 전체 면적의 {area_ratio*100:.1f}% 차지", use_container_width=True)
    
    st.header("3. 작업 이미지 업로드 (다중 선택)")
    target_files = st.file_uploader("고화질 변환을 진행할 사진들을 선택하세요", 
                                   type=['jpg', 'png', 'jpeg'], 
                                   accept_multiple_files=True)
    
    if target_files:
        processed_data = []
        cols = st.columns(4)
        
        for idx, file in enumerate(target_files):
            # 면적 기반 리사이징 실행
            result = resize_by_area(Image.open(file), target_size, area_ratio)
            
            with cols[idx % 4]:
                st.image(result, caption=file.name, use_container_width=True)
            
            # 화질 저하 절대 방지 옵션: quality=100, subsampling=0
            buf = io.BytesIO()
            result.save(buf, format="JPEG", quality=100, subsampling=0)
            processed_data.append((file.name, buf.getvalue()))
        
        if processed_data:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "a") as f:
                for name, data in processed_data:
                    f.writestr(f"opt_{name}", data)
            
            st.divider()
            st.download_button(
                "📦 초고화질 결과물 일괄 다운로드 (ZIP)",
                zip_buf.getvalue(),
                "batch_optimized_images.zip",
                "application/zip"
            )
else:
    st.info("먼저 왼쪽 사이드바에서 출력 사이즈를 지정하고, 기준이 될 레퍼런스 이미지를 업로드해 주세요.")
