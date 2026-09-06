import { useAuth } from "../lib/auth";

export function DoctorPatientsPage() {
  const { user, logout } = useAuth();
  return (
    <main className="p-6 space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Patients of {user?.display_name}</h1>
        <button onClick={logout} className="text-sm text-blue-600 underline">Sign out</button>
      </header>
      <p className="text-gray-600">Your patient list will appear here.</p>
    </main>
  );
}
