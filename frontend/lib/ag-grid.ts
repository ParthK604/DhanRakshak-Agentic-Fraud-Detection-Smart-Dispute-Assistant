import { AllCommunityModule, ModuleRegistry, themeQuartz } from "ag-grid-community";
import {
  AllCommunityModule as AllChartCommunityModule,
  ModuleRegistry as ChartModuleRegistry,
} from "ag-charts-community";

ModuleRegistry.registerModules([AllCommunityModule]);
ChartModuleRegistry.registerModules(AllChartCommunityModule);

export const gridTheme = themeQuartz.withParams({
  accentColor: "#0f766e",
  backgroundColor: "#ffffff",
  borderColor: "#dbe5e2",
  headerBackgroundColor: "#f4f8f7",
  headerFontWeight: 700,
  rowHoverColor: "#ecfdf5",
  foregroundColor: "#17332f",
});

export const defaultColDef = {
  sortable: true,
  resizable: true,
  minWidth: 110,
  flex: 1,
};
