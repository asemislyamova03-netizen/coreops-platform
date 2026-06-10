import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { listTemplates } from "../api/industry-templates";
import { listPlans } from "../api/subscriptions";
import { createTenant } from "../api/tenants";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Loading } from "../components/ui/Loading";
import { Select } from "../components/ui/Select";

function slugifyName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function TenantCreatePage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [planCode, setPlanCode] = useState("");
  const [templateCode, setTemplateCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const plansQuery = useQuery({ queryKey: ["plans"], queryFn: listPlans });
  const templatesQuery = useQuery({ queryKey: ["industry-templates"], queryFn: listTemplates });

  const mutation = useMutation({
    mutationFn: createTenant,
    onSuccess: (tenant) => {
      navigate(`/tenants/${tenant.id}`);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Не удалось создать tenant");
      }
    },
  });

  if (plansQuery.isLoading || templatesQuery.isLoading) {
    return <Loading />;
  }

  const handleNameChange = (value: string) => {
    setName(value);
    if (!slugTouched) {
      setSlug(slugifyName(value));
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    mutation.mutate({
      name,
      slug,
      ...(planCode ? { plan_code: planCode } : {}),
      ...(templateCode ? { industry_template_code: templateCode } : {}),
    });
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Создать tenant</h1>
          <p className="muted">Новая клиентская организация на платформе</p>
        </div>
        <Link to="/tenants">
          <Button variant="secondary">Назад к списку</Button>
        </Link>
      </div>

      <form className="form-card" onSubmit={handleSubmit}>
        {error && <Alert variant="error">{error}</Alert>}
        <Input
          label="Название"
          name="name"
          required
          value={name}
          onChange={(e) => handleNameChange(e.target.value)}
        />
        <Input
          label="Slug"
          name="slug"
          required
          pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
          title="Только строчные латинские буквы, цифры и дефисы"
          value={slug}
          onChange={(e) => {
            setSlugTouched(true);
            setSlug(e.target.value);
          }}
        />
        <Select
          label="Тарифный план"
          name="plan_code"
          emptyLabel="без плана"
          value={planCode}
          onChange={(e) => setPlanCode(e.target.value)}
          options={(plansQuery.data ?? []).map((plan) => ({
            value: plan.code,
            label: `${plan.name} (${plan.code})`,
          }))}
        />
        <Select
          label="Industry template"
          name="industry_template_code"
          emptyLabel="без шаблона"
          value={templateCode}
          onChange={(e) => setTemplateCode(e.target.value)}
          options={(templatesQuery.data ?? [])
            .filter((t) => t.is_active)
            .map((template) => ({
              value: template.code,
              label: `${template.name} (${template.code})`,
            }))}
        />
        <div className="actions-row">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Создание..." : "Создать"}
          </Button>
        </div>
      </form>
    </div>
  );
}
