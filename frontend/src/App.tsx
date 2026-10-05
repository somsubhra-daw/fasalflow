import { Navigate, Route, Routes } from "react-router-dom";

const Placeholder = ({ title }: { title: string }) => <main><h1>{title}</h1></main>;

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Placeholder title="FasalFlow Login" />} />
      <Route path="/farmer/*" element={<Placeholder title="Farmer Dashboard" />} />
      <Route path="/cold-store/*" element={<Placeholder title="Cold Store Dashboard" />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}