import { BrowserRouter, Route, Routes } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MyApplications from "./pages/MyApplications";
import SignIn from "./pages/SignIn";
import Verify from "./pages/Verify";
import Where from "./pages/Where";
import Results from "./pages/Results";
import Start from "./pages/Start";
import UsePicker from "./pages/UsePicker";
import ApplyStart from "./pages/ApplyStart";
import Wizard from "./pages/Wizard";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signin/verify" element={<Verify />} />
          <Route path="/my-applications" element={<MyApplications />} />
          <Route path="/where" element={<Where />} />
          <Route path="/start" element={<Start />} />
          <Route path="/start/use" element={<UsePicker />} />
          <Route path="/start/results" element={<Results />} />
          <Route path="/apply/:formKey" element={<ApplyStart />} />
          <Route path="/applications/:id" element={<Wizard />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
