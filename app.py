import streamlit as st
from PIL import Image, ImageChops
import io
import zipfile

def resize_with_margin(img, canvas_size=(1000, 1000), margin_rate=0.1):
    img = img.convert("RGBA")
    
    # 1. 배경이 흰색이라고 가정하고 피사체 영역(Bounding Box) 찾기
    bg = Image.new(img.mode, img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    
    if not bbox:
        return img.convert("RGB")
    
    # 2. 피사체 크롭 및 리사이징
    product = img.crop(bbox)
    target_max_w = canvas_size[0] * (1 - 2 * margin_rate)
    target_max_h = canvas_size[1] * (1 - 2 * margin_rate)
    
    product.thumbnail((target_max_w, target_max_h), Image.LANCZOS)
    
    # 3. 새 캔버스 생성 및 중앙 배치
    new_canvas = Image.new("RGB", canvas_size, (255, 255, 255))
    offset = (
        int((canvas_size[0] - product.width) / 2),
        int((canvas_size[1] - product.height) / 2)
    )
    new_canvas.paste(product, offset, product if product.mode == 'RGBA' else None)
    return new_canvas

# --- Streamlit UI ---
st.set_page_config(page_title="Bronson MD Image Tool", layout="wide")
st.title("📸 패션 MD용 제품컷 자동 리사이징 도구")
st.info("이미지의 여백을 인식하여 설정한 가이드에 맞게 일괄 조정합니다.")

# 사이드바 설정
st.sidebar.header("⚙️ 설정 가이드")
canvas_w = st.sidebar.number_input("캔버스 가로(px)", value=1000)
canvas_h = st.sidebar.number_input("캔버스 세로(px)", value=1000)
margin_pct = st.sidebar.slider("여백 비율 (%)", 0, 40, 10) / 100

uploaded_files = st.file_uploader("제품 사진을 업로드하세요 (다중 선택 가능)", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True)

if uploaded_files:
    processed_images = []
    
    cols = st.columns(4) # 미리보기 4열 배치
    for idx, uploaded_file in enumerate(uploaded_files):
        image = Image.open(uploaded_file)
        # 리사이징 실행
        result_img = resize_with_margin(image, (canvas_w, canvas_h), margin_pct)
        
        # 미리보기 표시
        with cols[idx % 4]:
            st.image(result_img, caption=uploaded_file.name, use_container_width=True)
        
        # 다운로드용 메모리 저장
        img_byte_arr = io.BytesIO()
        result_img.save(img_byte_arr, format='JPEG', quality=90)
        processed_images.append((uploaded_file.name, img_byte_arr.getvalue()))

    # 압축 파일 다운로드 버튼
    if processed_images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
            for name, data in processed_images:
                zip_file.writestr(f"resized_{name}", data)
        
        st.sidebar.markdown("---")
        st.sidebar.download_button(
            label="📦 리사이징 이미지 일괄 다운로드 (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="bronson_resized_images.zip",
            mime="application/zip"
        )
