import { Routes, Route } from "react-router-dom";
import Bookshelf from "./pages/Bookshelf";
import Creator from "./pages/Creator";
import Viewer from "./pages/Viewer";
import NotFound from "./pages/NotFound";
import Header from "./components/Header";

function App() {
  return (
    <>
      {/* 여기에 Header나 Footer처럼 모든 페이지에 공통으로 들어갈 컴포넌트를 둘 수 있습니다. */}
      <div className="flex flex-col min-h-screen w-full justify-start bg-green-100">
        <Header />
        <div className="flex-1 w-full h-full max-w-7xl mx-auto  bg-amber-100">
          <Routes>
            {/* 메인 페이지 */}
            <Route path="/" element={<Bookshelf />} />

            {/* 책 만들기 페이지 */}
            <Route path="/create" element={<Creator />} />

            {/* 책 뷰어 페이지 (:bookId는 동적으로 변하는 값) */}
            <Route path="/book/:bookId" element={<Viewer />} />

            {/* 정해진 경로 외 모든 경로 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </div>
    </>
  );
}

export default App;
