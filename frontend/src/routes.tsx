import { createBrowserRouter, Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth, type Role } from "./lib/auth";
import { LoginPage } from "./pages/LoginPage";
import { PatientHomePage } from "./pages/PatientHomePage";
import { DoctorPatientsPage } from "./pages/DoctorPatientsPage";

export function homeFor(role: Role): string {
  return role === "doctor" ? "/doctor" : "/patient";
}

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <p className="p-6 text-gray-500">Loading…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}

export function RoleHome() {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-6 text-gray-500">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homeFor(user.role)} replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/", element: <RoleHome /> },
  {
    path: "/patient",
    element: (
      <RequireRole role="patient">
        <PatientHomePage />
      </RequireRole>
    ),
  },
  {
    path: "/doctor",
    element: (
      <RequireRole role="doctor">
        <DoctorPatientsPage />
      </RequireRole>
    ),
  },
]);
