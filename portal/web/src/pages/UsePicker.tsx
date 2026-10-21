import { useNavigate } from "react-router";
import UseSearch from "../components/UseSearch";
import { loadAnswers, saveAnswers } from "../screener";

export default function UsePicker() {
  const navigate = useNavigate();

  function choose(useKey: string) {
    const answers = loadAnswers();
    if (answers) saveAnswers({ ...answers, use_key: useKey });
    navigate("/start/results");
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">What will the land or building be used for?</h1>
      <UseSearch onChoose={choose} />
    </div>
  );
}
