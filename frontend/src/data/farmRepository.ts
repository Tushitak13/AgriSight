import {
  chartSeries,
  dashboardSensors,
  experienceEntries,
  interventions,
  recommendationReasons,
  sensors,
  cropPreviewUrl,
  type SensorReading,
} from './farm';

/**
 * Read model consumed by the UI. The demo implementation below has no network
 * dependency. Replace it with an adapter only when an actual FastAPI response
 * contract is available; this module intentionally guesses no endpoint paths.
 */
export interface FarmRepository {
  getSensors(): readonly SensorReading[];
  getDashboardSensors(): readonly SensorReading[];
  getRecommendationReasons(): typeof recommendationReasons;
  getExperienceEntries(): typeof experienceEntries;
  getInterventions(): typeof interventions;
  getChartSeries(): typeof chartSeries;
  getCameraPreviewUrl(): string;
}

export const sampleFarmRepository: FarmRepository = {
  getSensors: () => sensors,
  getDashboardSensors: () => dashboardSensors,
  getRecommendationReasons: () => recommendationReasons,
  getExperienceEntries: () => experienceEntries,
  getInterventions: () => interventions,
  getChartSeries: () => chartSeries,
  getCameraPreviewUrl: () => cropPreviewUrl,
};

export const farmRepository = sampleFarmRepository;
