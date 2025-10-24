import { useState, useRef } from "react";

export default function StoryInput({
  page,
  updatePage,
  removePage,
  isRemovable,
}) {
  // 이미지 파일을 브라우저에서 미리 보여주기 위한 상태
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);

  // 이미지 파일이 선택되었을 때 호출되는 함수
  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      updatePage(page.id, "image", file);
      // FileReader를 사용하여 이미지 미리보기 생성
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // 텍스트가 변경될 때마다 부모 컴포넌트의 상태를 업데이트
  const handleStoryChange = (e) => {
    updatePage(page.id, "story", e.target.value);
  };

  // 이미지 아이콘 클릭 시 파일 선택창을 띄움
  const handleImageClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="flex items-start gap-4 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
      <input
        type="file"
        accept="image/*"
        onChange={handleImageChange}
        ref={fileInputRef}
        className="hidden" // 실제 input은 숨김
      />
      {/* 이미지 업로드 영역 */}
      <div
        onClick={handleImageClick}
        className="relative w-40 h-40 flex-shrink-0 bg-gray-100 rounded-md flex items-center justify-center cursor-pointer overflow-hidden"
      >
        {preview ? (
          <img
            src={preview}
            alt="Preview"
            className="w-full h-full object-cover"
          />
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-10 w-10 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>

      {/* 텍스트 입력 영역 */}
      <div className="flex-1 relative">
        <textarea
          value={page.story}
          onChange={handleStoryChange}
          placeholder="사진에 대한 설명을 적어주세요"
          className="w-full h-40 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* 삭제 버튼 */}
      {isRemovable && (
        <button
          onClick={() => removePage(page.id)}
          className="text-gray-400 hover:text-red-500"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
