import SignInForm from "../components/SignInForm";

export default function SignIn() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-[30px] font-bold">Sign in</h1>
      <SignInForm />
    </div>
  );
}
