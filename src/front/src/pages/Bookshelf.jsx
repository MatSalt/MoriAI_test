import { Link } from "react-router-dom";

const mockBooks = [
  {
    id: "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    title: "나의 첫 우주여행",
    coverImage:
      "https://placehold.co/400x600/6366f1/ffffff?text=My+First\nSpace+Trip",
    status: "success",
  },
  {
    id: "b2c3d4e5-f6a7-8901-2345-67890abcdef1",
    title: "마법 숲의 비밀",
    coverImage:
      "https://placehold.co/400x600/22c55e/ffffff?text=The+Secret+of\nMagic+Forest",
    status: "success",
  },
  {
    id: "c3d4e5f6-a7b8-9012-3456-7890abcdef12",
    title: "용감한 꼬마 기사",
    coverImage:
      "https://placehold.co/400x600/f97316/ffffff?text=Brave\nLittle+Knight",
    status: "success",
  },
  {
    id: "d4e5f6a7-b8c9-0123-4567-890abcdef123",
    title: "바닷속 친구들",
    coverImage:
      "https://placehold.co/400x600/3b82f6/ffffff?text=Friends\nUnder+the+Sea",
    status: "success",
  },
  {
    id: "e5f6a7b8-c9d0-1234-5678-90abcdef1234",
    title: "하늘을 나는 코끼리",
    // 'process' 상태일 때는 커버 이미지가 아직 없을 수 있습니다.
    coverImage: null,
    status: "process",
  },
  {
    id: "f6a7b8c9-d0e1-2345-6789-0abcdef12345",
    title: "장난감들의 파티",
    coverImage:
      "https://placehold.co/400x600/ec4899/ffffff?text=The+Toy\nParty",
    status: "success",
  },
  {
    id: "a7b8c9d0-e1f2-3456-7890-bcdef1234567",
    title: "실패한 동화책",
    // 'error' 상태일 때의 UI를 테스트하기 위한 데이터입니다.
    coverImage: null,
    status: "error",
  },
];

export default function Bookshelf() {
  return (
    <div className="p-8 bg-amber-200">
      <div className="flex justify-end mb-6">
        <button className="bg-white border border-black px-[10px] py-[10px] text-[14px]">
          편집버튼
        </button>
      </div>
      <div className="flex flex-wrap w-full gap-[65px]">
        {mockBooks.map((book, index) => (
          <Link to={"book/" + index}>
            <div className="w-[162px] h-[215px] bg-blue-400 rounded-lg">
              {book.title}
              {index}
            </div>
          </Link>
        ))}
        <Link to="/create">
          <div className="w-[162px] h-[215px] border-2 border-black border-dashed border-radius rounded-lg">
          책 생성하기
          </div>
        </Link>
      </div>
    </div>
  );
}
