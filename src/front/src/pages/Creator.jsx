import { useState } from "react";
import { useNavigate } from "react-router-dom";
import StoryInput from "../components/StoryInput";
// import axios from "axios";

export default function Creator() {
  const navigate = useNavigate();
  // 각 페이지의 데이터를 배열로 관리합니다.
  const [pages, setPages] = useState([{ id: 1, image: null, story: "" }]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 새 페이지 추가 함수
  const addPage = () => {
    // 최대 10개까지만 추가 가능하도록 제한
    if (pages.length >= 10) {
      alert("동화는 최대 10페이지까지 만들 수 있어요.");
      return;
    }
    const newPage = { id: Date.now(), image: null, story: "" };
    setPages([...pages, newPage]);
  };

  // 특정 페이지 삭제 함수
  const removePage = (id) => {
    if (pages.length > 1) {
      setPages(pages.filter((page) => page.id !== id));
    } else {
      alert("최소 한 페이지는 있어야 해요.");
    }
  };

  // 페이지 내용 업데이트 함수 (StoryInput 컴포넌트에서 호출)
  const updatePage = (id, field, value) => {
    setPages(
      pages.map((page) => (page.id === id ? { ...page, [field]: value } : page))
    );
  };

  // 서버에 데이터 전송하는 함수
  const handleSubmit = async () => {
    setIsSubmitting(true);

    const formData = new FormData();
    const stories = pages.map((page) => page.story);
    const images = pages.map((page) => page.image);

    // 모든 페이지에 이미지와 스토리가 있는지 확인
    if (images.some((img) => !img) || stories.some((s) => s.trim() === "")) {
      alert("모든 페이지에 이미지와 이야기를 채워주세요.");
      setIsSubmitting(false);
      return;
    }

    // FormData에 데이터 추가
    stories.forEach((story) => formData.append("stories", story));
    images.forEach((image) => formData.append("images", image));

    try {
      // --- API 요청 부분 ---
      // 실제 API 엔드포인트로 교체해야 합니다.
      // const response = await axios.post('/api/create-story', formData, {
      //   headers: {
      //     'Content-Type': 'multipart/form-data',
      //   },
      // });

      // 임시로 성공 시뮬레이션
      await new Promise((resolve) => setTimeout(resolve, 2000));
      console.log("전송 성공:", { stories, images });

      alert("생성 완료까지 10분 걸림");
      navigate("/"); // 성공 시 책장 페이지로 이동
    } catch (error) {
      console.error("전송 실패:", error);
      alert("오류가 발생했어요. 다시 시도해주세요.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto mt-6 mb-10">
      <div className="flex justify-end items-center mb-6">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="bg-blue-500 text-white rounded-md px-5 py-2 text-sm font-semibold hover:bg-blue-600 transition-colors disabled:bg-gray-400"
        >
          {isSubmitting ? "만드는 중..." : "생성 완료"}
        </button>
      </div>

      <div className="space-y-4">
        {pages.map((page) => (
          <StoryInput
            key={page.id}
            page={page}
            updatePage={updatePage}
            removePage={removePage}
            isRemovable={pages.length > 1}
          />
        ))}
      </div>

      <button
        onClick={addPage}
        className="w-full mt-4 flex items-center justify-center h-20 border-2 border-dashed border-gray-300 rounded-lg text-gray-400 hover:bg-gray-100 hover:border-gray-400 transition-all"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-8 w-8"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 4v16m8-8H4"
          />
        </svg>
      </button>
    </div>
  );
}
