import { BrowserRouter, Route, Routes } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MyApplications from "./pages/MyApplications";
import SignIn from "./pages/SignIn";
import Verify from "./pages/Verify";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signin/verify" element={<Verify />} />
          <Route path="/my-applications" element={<MyApplications />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
