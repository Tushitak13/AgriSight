import { CloudRain, Droplets, SunMedium, Thermometer, Waves, type LucideIcon } from 'lucide-react';

export type SensorId = 'soil' | 'temperature' | 'humidity' | 'water' | 'light' | 'rain';
export type WeatherState = 'SUNNY' | 'CLOUDY' | 'RAIN' | 'HEAVY_RAIN' | 'NO_DATA';

export interface SensorReading {
  id: SensorId;
  name: string;
  value: string;
  unit: string;
  status: string;
  tone: 'healthy' | 'warning' | 'info' | 'neutral';
  reliability: number;
  reliabilityText: string;
  updated: string;
  Icon: LucideIcon;
  series: number[];
  detail: string;
}

export const cropPreviewUrl = '/manus-storage/async-images/YGQ6re8RsmFVS8zBBcs6VC/image-1.webp';
export const demoLabel = 'Demo data';

export const sensors: SensorReading[] = [
  { id: 'temperature', name: 'Temperature', value: '31.4', unit: '°C', status: 'Normal', tone: 'healthy', reliability: 96, reliabilityText: 'Stable', updated: 'Just now', Icon: Thermometer, series: [29, 30, 29.5, 31, 30.5, 32, 31.4], detail: 'The current temperature is within the comfortable range for this sample field.' },
  { id: 'humidity', name: 'Humidity', value: '67', unit: '%', status: 'Normal', tone: 'healthy', reliability: 95, reliabilityText: 'Stable', updated: 'Just now', Icon: Waves, series: [64, 66, 65, 68, 66, 69, 67], detail: 'Ambient humidity is steady, helping put the dry soil reading in context.' },
  { id: 'soil', name: 'Soil Moisture', value: '38', unit: '%', status: 'Dry', tone: 'warning', reliability: 94, reliabilityText: 'Stable', updated: 'Just now', Icon: Droplets, series: [49, 47, 45, 43, 41, 39, 38], detail: 'Moisture has gradually declined. This is the main reason irrigation is recommended.' },
  { id: 'water', name: 'Water Available', value: '1,700', unit: 'L', status: 'Sufficient', tone: 'healthy', reliability: 98, reliabilityText: 'Stable', updated: 'Just now', Icon: Waves, series: [1800, 1770, 1760, 1750, 1730, 1710, 1700], detail: 'Available water is sufficient for the recommended irrigation in this sample scenario.' },
  { id: 'light', name: 'Light', value: '420', unit: 'lux', status: 'Moderate', tone: 'info', reliability: 91, reliabilityText: 'Stable', updated: 'Just now', Icon: SunMedium, series: [360, 390, 440, 460, 430, 410, 420], detail: 'Light is moderate at the time of this sample reading.' },
  { id: 'rain', name: 'Rain', value: '0', unit: 'mm', status: 'Sunny', tone: 'neutral', reliability: 93, reliabilityText: 'Stable', updated: 'Just now', Icon: CloudRain, series: [0, 0, 0, 0, 0, 0, 0], detail: 'No rainfall is present in the current sample state.' },
];

export const dashboardSensors = sensors.filter((sensor) => sensor.id !== 'rain');

export const recommendationReasons = [
  { label: 'Soil condition', value: 'Dry', tone: 'warning' },
  { label: 'Rain condition', value: 'None', tone: 'neutral' },
  { label: 'Water availability', value: 'Sufficient', tone: 'healthy' },
  { label: 'Sensor reliability', value: '94%', tone: 'healthy' },
  { label: 'Historical similarity', value: 'High', tone: 'healthy' },
];

export const experienceEntries = [
  { date: 'June 14', conditions: 'Soil moisture 35%', action: 'Irrigation', before: '35%', after: '62%', result: 'Successful', similarity: '92%' },
  { date: 'June 02', conditions: 'Soil moisture 37%', action: 'Irrigation', before: '37%', after: '59%', result: 'Successful', similarity: '87%' },
  { date: 'May 28', conditions: 'Soil moisture 39%', action: 'Waited for rain', before: '39%', after: '35%', result: 'Declined', similarity: '81%' },
];

export const interventions = [
  { date: 'Oct 7', action: 'Irrigation', before: '35%', after: '61%', result: 'Successful' },
  { date: 'Oct 6', action: 'Irrigation', before: '37%', after: '58%', result: 'Successful' },
  { date: 'Oct 5', action: 'No action', before: '39%', after: '34%', result: 'Declined' },
];

export type ChartMetric = 'soil' | 'temperature' | 'humidity' | 'water' | 'waterUsage';

export const chartSeries: Record<ChartMetric, number[]> = {
  soil: [61, 57, 56, 53, 50, 48, 46, 45, 43, 42, 40, 38],
  temperature: [27, 28, 27, 29, 30, 31, 32, 31, 33, 32, 31, 31.4],
  humidity: [61, 63, 64, 62, 65, 66, 64, 68, 69, 67, 66, 67],
  water: [2130, 2070, 2000, 1950, 1880, 1830, 1790, 1750, 1720, 1700, 1700, 1700],
  waterUsage: [0, 12, 8, 24, 37, 18, 45, 31, 0, 54, 42, 55],
};

export const weatherOptions: Array<{ state: WeatherState; label: string }> = [
  { state: 'SUNNY', label: 'Sunny' },
  { state: 'CLOUDY', label: 'Cloudy' },
  { state: 'RAIN', label: 'Rain' },
  { state: 'HEAVY_RAIN', label: 'Heavy rain' },
  { state: 'NO_DATA', label: 'No data' },
];
