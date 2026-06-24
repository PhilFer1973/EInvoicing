import { CircleHelp, FileSpreadsheet, Settings } from "lucide-react";

import type { View } from "../types";
import { workbookTemplateUrl } from "../services/api";

interface TopNavProps {
  activeView: View;
  onViewChange: (view: View) => void;
}

export function TopNav({ activeView, onViewChange }: TopNavProps) {
  return (
    <header className="top-nav">
      <button className="brand" onClick={() => onViewChange("workbench")} type="button">
        Global E-Invoice Generation
      </button>
      <nav aria-label="Primary navigation">
        <button
          className={activeView === "workbench" ? "nav-link active" : "nav-link"}
          onClick={() => onViewChange("workbench")}
          type="button"
        >
          E-Invoicing
        </button>
        <button
          className={activeView === "audit" ? "nav-link active" : "nav-link"}
          onClick={() => onViewChange("audit")}
          type="button"
        >
          Audit Trail
        </button>
      </nav>
      <div className="top-actions">
        <a className="icon-text-button" href={workbookTemplateUrl()} title="Download blank Excel template">
          <FileSpreadsheet aria-hidden="true" size={17} />
          <span>Export Template</span>
        </a>
        <button className="icon-text-button" type="button" title="Settings">
          <Settings aria-hidden="true" size={17} />
          <span>Settings</span>
        </button>
        <button className="icon-text-button" type="button" title="Help">
          <CircleHelp aria-hidden="true" size={17} />
          <span>Help</span>
        </button>
      </div>
    </header>
  );
}
