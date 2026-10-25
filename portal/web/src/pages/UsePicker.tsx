import { useNavigate } from "react-router";
import UseSearch from "../components/UseSearch";
import { loadAnswers, saveAnswers } from "../screener";

export default function UsePicker() {
  const navigate = useNavigate();

  function choose(useKey: string) {
    const answers = loadAnswers();
    if (answers) saveAnswers({ ...answers, use_key: useKey });
    navigate("/start/needs");
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-[20px] font-medium leading-[1.3]">What will the land or building be used for?</h2>
      <UseSearch onChoose={choose} />
    </div>
  );
}
