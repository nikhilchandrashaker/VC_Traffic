# Data dictionary (all values simulated)
## observations.csv (one row per segment per 15 minutes)
| Field | Meaning |
|---|---|
| timestamp, segment_id | Interval start (local, no tz); key to segments.csv |
| volume_veh_15min | Vehicles in the interval |
| avg_speed_mph | Space-mean speed |
| density_veh_per_mile_per_lane | volume x 4 / speed / lanes |
| travel_time_index | free-flow speed / speed (1.0 = free flow) |
| queue_length_ft | Estimated queue length |
| congestion_level | 0 free (>=0.85 of free flow), 1 light (>=0.70), 2 moderate (>=0.55), 3 heavy (>=0.40), 4 severe |
| incident_active | 1 if an incident is active on the segment |
| is_weekend, is_holiday, is_peak_hour | Calendar flags (peaks 6:30-9:00, 15:30-18:30 weekdays) |
| fuel_gal, co2_kg | Estimated fuel and CO2 from a speed-based fuel-economy curve |
| signal_delay_s_per_veh | Uniform-delay estimate (arterials only; blank otherwise) |
| bus_delay_min, bus_boardings_15min | Transit delay and boardings (arterials only) |
| precip_mm_15min | Rain in the interval (also in weather.csv) |
## segments.csv
segment_id, segment_name, road, road_type, lanes, speed_limit_mph, length_mi, signals, profile (in/out/mix peak direction), peak_load (demand/capacity at peak), free_flow_mph, cap_per_lane_vph, has_transit, downstream_ids, upstream_ids (flow graph, `;`-separated).
## weather.csv: timestamp, precip_mm_15min, temp_f, visibility_mi, wind_mph
## incidents.csv: incident_id, segment_id, start_time, duration_min, incident_type, severity (1-3), capacity_multiplier
## signals.csv: signal_id, segment_id, cycle_s, offset_s, main_green_s, side_green_s, control_type
## simulation_results.csv: scenario, controller, mean_delay_s, ci95, mean_total_queue, max_total_queue
