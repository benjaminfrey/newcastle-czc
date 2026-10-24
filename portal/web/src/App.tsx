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
import ApplicationPage from "./app/ApplicationPage";
import Review from "./pages/Review";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signin/verify" element={<Verify />} />
          <Route path="/my-applications" element={<MyApplications />} />
          <Route path="/where" element={<Where />} />
          <Route path="/start" element={<Start />} />
          <Route path="/start/use" element={<UsePicker />} />
          <Route path="/start/results" element={<Results />} />
          <Route path="/apply/:formKey" element={<ApplyStart />} />
          <Route path="/applications/:id/review" element={<Review />} />
        </Route>
        {/* The application window draws its own chrome. */}
        <Route path="/applications/:id/:stepId?" element={<ApplicationPage />} />
      </Routes>
    </BrowserRouter>
  );
}
