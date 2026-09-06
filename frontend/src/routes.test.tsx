import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext, type AuthValue, type User } from "./lib/auth";
import { RequireRole, RoleHome } from "./routes";

const patient: User = { id: "1", email: "p@x.dev", role: "patient", display_name: "Pat" };
const doctor: User = { id: "2", email: "d@x.dev", role: "doctor", display_name: "Doc" };

function renderAt(path: string, user: User | null, loading = false) {
  const value: AuthValue = { user, loading, login: async () => user!, logout: () => {} };
  return render(
    <AuthContext.Provider value={value}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>login page</div>} />
          <Route path="/" element={<RoleHome />} />
          <Route path="/patient" element={<RequireRole role="patient"><div>patient home</div></RequireRole>} />
          <Route path="/doctor" element={<RequireRole role="doctor"><div>doctor home</div></RequireRole>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("RequireRole", () => {
  it("redirects anonymous users to login", () => {
    renderAt("/patient", null);
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("renders the child for the matching role", () => {
    renderAt("/patient", patient);
    expect(screen.getByText("patient home")).toBeInTheDocument();
  });

  it("sends the wrong role to its own home", () => {
    renderAt("/doctor", patient);
    expect(screen.getByText("patient home")).toBeInTheDocument();
  });

  it("shows a loading state while the session is being restored", () => {
    renderAt("/patient", null, true);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });
});

describe("RoleHome", () => {
  it("routes doctors to /doctor", () => {
    renderAt("/", doctor);
    expect(screen.getByText("doctor home")).toBeInTheDocument();
  });

  it("routes patients to /patient", () => {
    renderAt("/", patient);
    expect(screen.getByText("patient home")).toBeInTheDocument();
  });

  it("sends anonymous users to login", () => {
    renderAt("/", null);
    expect(screen.getByText("login page")).toBeInTheDocument();
  });
});
