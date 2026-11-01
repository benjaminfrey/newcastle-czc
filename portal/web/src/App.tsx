import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import ProjectPage from "./app/ProjectPage";
import Home from "./pages/Home";
import Messages from "./pages/Messages";
import You from "./pages/You";
import Verify from "./pages/Verify";
import RequireSignIn from "./shell/RequireSignIn";
import NewProject from "./start/NewProject";

const HOME = <Navigate to="/" replace />;

// The guided builder's preview (plan 1 of the guided-builder spec): only in builds made with
// VITE_GUIDE_PREVIEW=1 (the LAN copy), and loaded on its own so HeroUI pages never load MUI.
const GUIDE_PREVIEW = import.meta.env.VITE_GUIDE_PREVIEW === "1";
const GuidePreview = lazy(() => import("./guide/GuidePreview"));

// Sign in first (projects brief §3): Home and the emailed link are the only pages a visitor sees
// signed out. "Do I need a permit?" is gone; its addresses, and the old application addresses,
// go Home.
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/signin/verify" element={<div className="mx-auto max-w-md px-4 py-10"><Verify /></div>} />
      <Route element={<RequireSignIn />}>
        <Route path="/new" element={<NewProject />} />
        <Route path="/projects/:id/:stepId?/:sub?" element={<ProjectPage />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/you" element={<You />} />
        {GUIDE_PREVIEW && <Route path="/guide/preview" element={<Suspense fallback={null}><GuidePreview /></Suspense>} />}
      </Route>
      {["/signin", "/where", "/start/*", "/my-applications", "/apply/*", "/applications/*"].map((p) => (
        <Route key={p} path={p} element={HOME} />
      ))}
      <Route path="*" element={HOME} />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
