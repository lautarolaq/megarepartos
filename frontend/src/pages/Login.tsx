import { Button } from "@/components/ui/Button";
import { startGoogleLogin } from "@/lib/auth";

export function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6 text-slate-800">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-md">
        <h1 className="text-2xl font-semibold tracking-tight">Megarepartos</h1>
        <p className="mt-2 text-sm text-slate-500">
          Plataforma de campañas de WhatsApp para negocios de reparto recurrente.
        </p>
        <div className="mt-6">
          <Button onClick={startGoogleLogin} className="w-full">
            Iniciar sesión con Google
          </Button>
        </div>
        <p className="mt-6 text-xs text-slate-400">
          Al continuar aceptás los términos de uso. Asegurate de tener el backend corriendo en
          localhost:8000 con OAuth configurado.
        </p>
      </div>
    </main>
  );
}
