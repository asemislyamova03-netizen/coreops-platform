interface PlaceholderWidget {
  title: string;
  description: string;
}

interface PlaceholderWidgetGridProps {
  widgets: PlaceholderWidget[];
}

export function PlaceholderWidgetGrid({ widgets }: PlaceholderWidgetGridProps) {
  return (
    <div className="workspace-widget-grid">
      {widgets.map((widget) => (
        <div key={widget.title} className="panel workspace-widget-card">
          <h3>{widget.title}</h3>
          <p className="muted">{widget.description}</p>
          <p className="workspace-widget-soon">Данные появятся в W2.2+</p>
        </div>
      ))}
    </div>
  );
}
