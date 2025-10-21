import { Link } from "react-router-dom";

export default function Header() {
  return (
    <div className="bg-white shadow-[0px_0px_6px_0px_rgba(0,0,0,0.12)] h-[80px] flex items-center justify-center gap-[20px] px-[20px]">
      <div className="bg-[rgba(0,0,0,0.1)] rounded-full size-[40px]" />
      <p className="flex-1 text-[28px] leading-[36px] text-black">모리아이</p>
      {/* <SettingsIcon /> */}
      <div className="flex items-center gap-2 text-sm">
        <Link to="/">내 책장</Link>
        <Link to="/create">책 만들기</Link>
      </div>
    </div>
  );
}
