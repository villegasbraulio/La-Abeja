import { type FormEvent, useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../../api/auth";
import { Button } from "../../components/ui/Button";
import { useAuthStore } from "../../store/authStore";

type AuthMode = "login" | "register";

const inputClass =
  "rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400";

function errorMessage(error: unknown, fallback: string) {
  const axiosError = error as AxiosError<Record<string, string[] | string>>;
  const data = axiosError.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? first[0] : fallback;
}

export function AccountPage() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const user = useAuthStore((state) => state.user);
  const setSession = useAuthStore((state) => state.setSession);
  const logout = useAuthStore((state) => state.logout);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [message, setMessage] = useState<string | null>(null);
  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [registerForm, setRegisterForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    password: "",
  });
  const [profileForm, setProfileForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    birth_date: "",
    newsletter_subscribed: false,
  });
  const [passwordForm, setPasswordForm] = useState({ old_password: "", new_password: "" });

  useEffect(() => {
    if (!user) return;
    setProfileForm({
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone,
      birth_date: user.birth_date ?? "",
      newsletter_subscribed: user.newsletter_subscribed,
    });
  }, [user]);

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(loginForm),
    onSuccess: (session) => {
      setSession({ accessToken: session.access, refreshToken: session.refresh, user: session.user });
      setMessage("Sesión iniciada.");
    },
    onError: (error) => setMessage(errorMessage(error, "No pudimos iniciar sesión.")),
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      authApi.register({
        ...registerForm,
        newsletter_subscribed: true,
        preferred_varietals: [],
      }),
    onSuccess: (session) => {
      setSession({ accessToken: session.access, refreshToken: session.refresh, user: session.user });
      setMessage("Cuenta creada.");
    },
    onError: (error) => setMessage(errorMessage(error, "No pudimos crear la cuenta.")),
  });

  const profileMutation = useMutation({
    mutationFn: () =>
      authApi.updateProfile({
        ...profileForm,
        birth_date: profileForm.birth_date || null,
      }),
    onSuccess: (updatedUser) => {
      if (accessToken && refreshToken) {
        setSession({ accessToken, refreshToken, user: updatedUser });
      }
      setMessage("Datos guardados.");
    },
    onError: (error) => setMessage(errorMessage(error, "No pudimos guardar tus datos.")),
  });

  const passwordMutation = useMutation({
    mutationFn: () => authApi.changePassword(passwordForm),
    onSuccess: () => {
      setPasswordForm({ old_password: "", new_password: "" });
      setMessage("Contraseña actualizada.");
    },
    onError: (error) => setMessage(errorMessage(error, "No pudimos cambiar la contraseña.")),
  });

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken);
    } finally {
      logout();
      navigate("/");
    }
  }

  function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (authMode === "login") {
      loginMutation.mutate();
      return;
    }
    registerMutation.mutate();
  }

  if (!accessToken || !user) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Cuenta
          </p>
          <h1 className="mt-3 font-serif text-4xl text-burgundy-950">
            Entrá para ver pedidos y administrar tus datos.
          </h1>

          <div className="mt-8 flex flex-wrap gap-3">
            {(["login", "register"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => {
                  setAuthMode(mode);
                  setMessage(null);
                }}
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  authMode === mode
                    ? "bg-burgundy-900 text-gold-300"
                    : "bg-cream-50 text-burgundy-800"
                }`}
              >
                {mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
              </button>
            ))}
          </div>

          <form className="mt-8 grid gap-5" onSubmit={handleAuthSubmit}>
            {authMode === "register" ? (
              <div className="grid gap-5 md:grid-cols-2">
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Nombre</span>
                  <input
                    value={registerForm.first_name}
                    onChange={(event) =>
                      setRegisterForm((current) => ({ ...current, first_name: event.target.value }))
                    }
                    className={inputClass}
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Apellido</span>
                  <input
                    value={registerForm.last_name}
                    onChange={(event) =>
                      setRegisterForm((current) => ({ ...current, last_name: event.target.value }))
                    }
                    className={inputClass}
                    required
                  />
                </label>
              </div>
            ) : null}

            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Email</span>
              <input
                type="email"
                value={authMode === "login" ? loginForm.email : registerForm.email}
                onChange={(event) =>
                  authMode === "login"
                    ? setLoginForm((current) => ({ ...current, email: event.target.value }))
                    : setRegisterForm((current) => ({ ...current, email: event.target.value }))
                }
                className={inputClass}
                required
              />
            </label>

            {authMode === "register" ? (
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Teléfono</span>
                <input
                  value={registerForm.phone}
                  onChange={(event) =>
                    setRegisterForm((current) => ({ ...current, phone: event.target.value }))
                  }
                  className={inputClass}
                />
              </label>
            ) : null}

            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Contraseña</span>
              <input
                type="password"
                value={authMode === "login" ? loginForm.password : registerForm.password}
                onChange={(event) =>
                  authMode === "login"
                    ? setLoginForm((current) => ({ ...current, password: event.target.value }))
                    : setRegisterForm((current) => ({ ...current, password: event.target.value }))
                }
                className={inputClass}
                required
              />
            </label>

            {message ? (
              <div className="rounded-lg border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
                {message}
              </div>
            ) : null}

            <Button type="submit" disabled={loginMutation.isPending || registerMutation.isPending}>
              {authMode === "login" ? "Ingresar" : "Crear cuenta"}
            </Button>
          </form>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-6xl px-6 py-16">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Mi cuenta
          </p>
          <h1 className="mt-3 font-serif text-4xl text-burgundy-950">
            {user.full_name || user.email}
          </h1>
          <p className="mt-2 text-burgundy-700">{user.email}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link to="/pedidos">
            <Button variant="ghost">Mis pedidos</Button>
          </Link>
          <Button type="button" variant="secondary" onClick={handleLogout}>
            Cerrar sesión
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <form
          className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet"
          onSubmit={(event) => {
            event.preventDefault();
            setMessage(null);
            profileMutation.mutate();
          }}
        >
          <h2 className="font-serif text-3xl text-burgundy-950">Datos personales</h2>
          <div className="mt-6 grid gap-5 md:grid-cols-2">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Nombre</span>
              <input
                value={profileForm.first_name}
                onChange={(event) =>
                  setProfileForm((current) => ({ ...current, first_name: event.target.value }))
                }
                className={inputClass}
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Apellido</span>
              <input
                value={profileForm.last_name}
                onChange={(event) =>
                  setProfileForm((current) => ({ ...current, last_name: event.target.value }))
                }
                className={inputClass}
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Teléfono</span>
              <input
                value={profileForm.phone}
                onChange={(event) =>
                  setProfileForm((current) => ({ ...current, phone: event.target.value }))
                }
                className={inputClass}
              />
            </label>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Fecha de nacimiento</span>
              <input
                type="date"
                value={profileForm.birth_date}
                onChange={(event) =>
                  setProfileForm((current) => ({ ...current, birth_date: event.target.value }))
                }
                className={inputClass}
              />
            </label>
          </div>
          <label className="mt-6 flex items-start gap-3 rounded-lg border border-burgundy-100 bg-cream-50 px-4 py-4 text-sm text-burgundy-900">
            <input
              type="checkbox"
              checked={profileForm.newsletter_subscribed}
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  newsletter_subscribed: event.target.checked,
                }))
              }
              className="mt-1 h-4 w-4 accent-burgundy-900"
            />
            Recibir novedades y propuestas de la bodega
          </label>
          <Button className="mt-6" type="submit" disabled={profileMutation.isPending}>
            {profileMutation.isPending ? "Guardando..." : "Guardar datos"}
          </Button>
        </form>

        <div className="space-y-6">
          <form
            className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet"
            onSubmit={(event) => {
              event.preventDefault();
              setMessage(null);
              passwordMutation.mutate();
            }}
          >
            <h2 className="font-serif text-3xl text-burgundy-950">Seguridad</h2>
            <div className="mt-6 grid gap-5">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Contraseña actual</span>
                <input
                  type="password"
                  value={passwordForm.old_password}
                  onChange={(event) =>
                    setPasswordForm((current) => ({ ...current, old_password: event.target.value }))
                  }
                  className={inputClass}
                  required
                />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Nueva contraseña</span>
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(event) =>
                    setPasswordForm((current) => ({ ...current, new_password: event.target.value }))
                  }
                  className={inputClass}
                  required
                />
              </label>
            </div>
            <Button className="mt-6" type="submit" disabled={passwordMutation.isPending}>
              Cambiar contraseña
            </Button>
          </form>

          {message ? (
            <div className="rounded-lg border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
              {message}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
