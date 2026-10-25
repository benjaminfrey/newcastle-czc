import { BrowserRouter, Route, Routes } from "react-router";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MyApplications from "./pages/MyApplications";
import SignIn from "./pages/SignIn";
import Verify from "./pages/Verify";
import Where from "./pages/Where";
import StartFlow, { Moved, StartSignIn } from "./start/StartFlow";
import Results from "./pages/Results";
import Start from "./pages/Start";
import UsePicker from "./pages/UsePicker";
import ApplyStart from "./pages/ApplyStart";
import ApplicationPage from "./app/ApplicationPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signin/verify" element={<Verify />} />
          <Route path="/my-applications" element={<MyApplications />} />
          <Route path="/where" element={<Moved to="/start/property" />} />
          <Route path="/start/results" element={<Moved to="/start/needs" />} />
          <Route path="/apply/:formKey" element={<ApplyStart />} />
        </Route>
        {/* "Do I need a permit?" and each application are windows that draw their own chrome. */}
        <Route element={<StartFlow />}>
          <Route path="/start" element={<Start />} />
          <Route path="/start/property" element={<Where />} />
          <Route path="/start/use" element={<UsePicker />} />
          <Route path="/start/needs" element={<Results />} />
          <Route path="/start/signin" element={<StartSignIn />} />
        </Route>
        <Route path="/applications/:id/:stepId?/:sub?" element={<ApplicationPage />} />
      </Routes>
    </BrowserRouter>
  );
}
