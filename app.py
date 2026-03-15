import streamlit as st
from PIL import Image, ImageChops
import io
import zipfile

def get_content_bbox(img):
    """이미지 내에서 실제 제품(비어있지 않은 영역)의 경계 상자를 찾는 함수"""
    # 투명 배경(RGBA) 또는 흰색 배경에서 제품 영역만 추출
    if img.mode != 'RGBA':
        img = img.convert("RGBA")
    
    # 배경(흰색/투명)과 다른 영역(제품) 찾기
    bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    
    # 만약 투명 배경이 아니라면 흰색 배경으로 다시 시도
    if not bbox:
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        
    return bbox

def get_margin_ratios(img):
    """레퍼런스 이미지에서 상하좌우 여백 비율을 계산"""
    bbox = get_content_bbox(img)
    if not bbox:
        return 0.1, 0.1, 0.1, 0.1 # 기본값 10%
        
    w, h = img.size
    # 제품 외곽선 기준 여백 계산 (좌, 상, 우, 하)
    m_left = bbox[0] / w
    m_top = bbox[1] / h
    m_right = (w - bbox[2]) / w
    m_bottom = (h - bbox[3]) / h
    return m_left, m_top, m_right, m_bottom

def resize_and_align(img, target_size, ratios):
    """추출된 여백 비율에 맞춰 제품을 중앙 정렬 및 리사이징"""
    bbox = get_content_bbox(img)
    if not bbox:
        return img.convert("RGB").resize(target_size)
    
    product = img.crop(bbox) # 제품 영역만 잘라냄
    m_left, m_top, m_right, m_bottom = ratios
    
    # 제품이 들어갈 수 있는 가용 영역 계산
    avail_w = target_size[0] * (1 - m_left - m_right)
    avail_h = target_size[1] * (1 - m_top - m_bottom)
    
    # 가용 영역에 맞춰 제품 리사이징 (비율 유지)
    product.thumbnail((avail_w, avail_h), Image.LANCZOS)
    
    # 새 캔버스 생성 및 배치
    new_canvas = Image.new("RGB", target_size, (255, 255, 255))
    
    # 계산된 여백을 유지하며 중앙 배치
    x_offset = int(target_size[0] * m_left + (avail_w - product.width) / 2)
    y_offset = int(target_size[1] * m_top + (avail_h - product.height) / 2)
    
    new_canvas.paste(product, (x_offset, y_offset), product if product.mode == 'RGBA' else None)
    return new_canvas

# --- UI 설정 ---
st.set_page_config(page_title="Bronson MD: Precision Resizer", layout="wide")
st.title("📏 제품컷 정밀 리사이징 도구")
st.markdown("누끼 작업이 완료된 이미지들을 **레퍼런스 여백**에 맞춰 일괄 조정합니다.")

st.sidebar.header("1. 레퍼런스 설정")
ref_file = st.sidebar.file_uploader("여백 기준이 될 이미지", type=['jpg', 'png', 'jpeg'])

if ref_file:
    ref_img = Image.open(ref_file)
    ratios = get_margin_ratios(ref_img)
    st.sidebar.image(ref_img, caption="이 이미지의 여백을 분석했습니다.", use_container_width=True)
    
    st.divider()
    
    st.header("2. 작업 이미지 업로드")
    target_files = st.file_uploader("리사이징할 사진들을 선택하세요 (다중 선택 가능)", 
                                   type=['jpg', 'png', 'jpeg'], 
                                   accept_multiple_files=True)
    
    if target_files:
        processed_data = []
        cols = st.columns(4)
        
        for idx, file in enumerate(target_files):
            result = resize_and_align(Image.open(file), (1000, 1000), ratios)
            
            with cols[idx % 4]:
                st.image(result, caption=f"완료: {file.name}", use_container_width=True)
            
            # 다운로드용 저장
            buf = io.BytesIO()
            result.save(buf, format="JPEG", quality=95)
            processed_data.append((file.name, buf.getvalue()))
        
        if processed_data:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "a") as f:
                for name, data in processed_data:
                    f.writestr(f"resized_{name}", data)
            
            st.sidebar.divider()
            st.sidebar.download_button(
                "📦 결과물 일괄 다운로드 (ZIP)",
                zip_buf.getvalue(),
                "bronson_batch_resized.zip",
                "application/zip"
            )
else:
    st.warning("먼저 왼쪽 사이드바에서 기준이 될 레퍼런스 이미지를 업로드해 주세요.")
