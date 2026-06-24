// Keyword index for the config category-rail Filter… box (console redesign).
//
// Maps each rail section to searchable terms — the visible field labels AND the
// underlying snake_case TOML keys rendered in that section — so the filter can
// surface a section by an individual parameter name or its TOML key, not just
// the nav label. Presentation-only; derived from the fields rendered in
// ProcessingConfigTabs, configToBackend (TOML keys) and optionMeta (labels).
//
// Terms include both the human label ("elevation mask") and the dotted TOML key
// ("positioning.elevation_mask") so either typing style matches via substring.

const SECTION_SEARCH: Record<string, string[]> = {
  'input-files': [
    'time start', 'time end', 'interval', 'rover obs', 'rover observation', 'navigation',
    'base obs', 'base observation', 'corrections', 'precise ephemeris', 'output file',
    'rover_obs', 'nav_file', 'base_obs', 'correction_files', 'output_file',
  ],

  streams: [
    'input streams', 'rover', 'base station', 'correction', 'output streams', 'log streams',
    'ntrip', 'tcp client', 'tcp server', 'serial', 'file', 'rtcm', 'ubx', 'sbf', 'binex',
    'rinex', 'clas l6', 'l6e', 'nmea', 'stream format', 'nmea request',
  ],

  mode: [
    'positioning mode', 'correction', 'correction provider', 'clas', 'madoca', 'igs', 'igs-rts',
    'galileo has', 'beidou b2b', 'ssr provider', 'positioning.correction', 'qzs-clas', 'qzs-madoca',
    'filter direction', 'solution type', 'frequencies', 'frequency',
    'signals', 'signal mode', 'elevation mask', 'snr mask', 'ionosphere', 'troposphere',
    'atmosphere', 'satellite ephemeris', 'ephemeris', 'constellations', 'gps', 'glonass',
    'galileo', 'qzss', 'sbas', 'beidou', 'irnss', 'excluded satellites',
    'positioning.positioning_mode', 'positioning.filter_type', 'positioning.frequency',
    'positioning.signals', 'positioning.signal_mode', 'positioning.elevation_mask',
    'positioning.snr_mask', 'positioning.atmosphere.ionosphere', 'positioning.atmosphere.troposphere',
    'positioning.satellite_ephemeris', 'positioning.ephemeris_option', 'positioning.constellations',
    'positioning.excluded_satellites',
    // Receiver Dynamics + Earth Tides + corrections toggles (relocated into Basic Strategy)
    'earth tides', 'tidal correction', 'receiver dynamics', 'sat pcv', 'rec pcv',
    'satellite antenna pcv', 'receiver antenna pcv', 'phase windup', 'reject eclipse',
    'exclude eclipse', 'raim fde', 'positioning.receiver_dynamics',
    'positioning.corrections.tidal_correction', 'positioning.corrections.satellite_antenna',
    'positioning.corrections.receiver_antenna', 'positioning.corrections.phase_windup',
    'positioning.corrections.exclude_eclipse', 'positioning.corrections.raim_fde',
  ],

  ar: [
    'ar mode', 'ambiguity resolution', 'glonass ar', 'beidou ar', 'bds ar', 'qzss ar',
    'ratio threshold', 'ar elevation mask', 'hold elevation mask', 'ratio 1', 'ratio 2',
    'ratio 3', 'ratio 4', 'ratio 5', 'ratio 6',
    'lock count', 'min fix epochs', 'max lambda iterations', 'outage reset count',
    'slip threshold', 'doppler', 'cycle slip', 'min ambiguities', 'max excluded sats',
    'min fix pairs', 'min drop pairs', 'min hold pairs', 'ar filter', 'partial ar',
    'ambiguity_resolution.mode', 'ambiguity_resolution.glonass_ar', 'ambiguity_resolution.bds_ar',
    'ambiguity_resolution.qzs_ar', 'ambiguity_resolution.thresholds.ratio',
    'ambiguity_resolution.thresholds.elevation_mask', 'ambiguity_resolution.thresholds.hold_elevation',
    'ambiguity_resolution.thresholds.ratio1',
    'ambiguity_resolution.counters.lock_count', 'ambiguity_resolution.counters.min_fix',
    'ambiguity_resolution.counters.max_iterations', 'ambiguity_resolution.counters.out_count',
    'ambiguity_resolution.partial_ar.min_ambiguities', 'ambiguity_resolution.partial_ar.ar_filter',
    'slip_detection.threshold', 'slip_detection.doppler',
  ],

  kf: [
    'kalman filter', 'iterations', 'sync solution', 'code phase ratio', 'phase error',
    'phase error base', 'phase error elevation', 'phase error baseline', 'doppler', 'ura ratio',
    'accel noise', 'acceleration noise', 'horizontal', 'vertical', 'iono noise', 'ifb noise',
    'clock stability', 'phase bias', 'process noise', 'ztd', 'position noise', 'iono time const',
    'initial std', 'initial standard deviation', 'measurement error',
    'kalman_filter.iterations', 'kalman_filter.sync_solution',
    'kalman_filter.measurement_error.code_phase_ratio_l1', 'kalman_filter.measurement_error.code_phase_ratio_l2',
    'kalman_filter.measurement_error.code_phase_ratio_l5', 'kalman_filter.measurement_error.phase',
    'kalman_filter.measurement_error.phase_elevation', 'kalman_filter.measurement_error.phase_baseline',
    'kalman_filter.measurement_error.doppler', 'kalman_filter.measurement_error.ura_ratio',
    'kalman_filter.process_noise.accel_h', 'kalman_filter.process_noise.accel_v',
    'kalman_filter.process_noise.iono_max', 'kalman_filter.process_noise.ifb',
    'kalman_filter.process_noise.clock_stability', 'kalman_filter.process_noise.bias',
    'kalman_filter.process_noise.position_h', 'kalman_filter.process_noise.position_v',
    'kalman_filter.initial_std.bias', 'kalman_filter.initial_std.ionosphere',
    'kalman_filter.initial_std.troposphere',
    // Rejection Criteria (merged into Kalman Filter from the former Advanced section)
    'rejection criteria', 'innovation threshold', 'l1 l2 residual', 'dispersive residual',
    'non-dispersive residual', 'hold chi-square', 'fix chi-square', 'max gdop', 'pseudorange diff',
    'pos error count', 'rejection.innovation', 'rejection.l1_l2_residual', 'rejection.dispersive',
    'rejection.non_dispersive', 'rejection.gdop',
  ],

  clas: [
    'clas', 'ppp-rtk', 'vrs', 'vrs-rtk', 'grid radius', 'grid selection radius', 'receiver type',
    'ar significance level', 'significance level', 'alpha', 'ambiguity_resolution.thresholds.alpha',
    'uncertainty x', 'uncertainty y', 'uncertainty z', 'position uncertainty',
    'positioning.clas.grid_selection_radius', 'positioning.clas.receiver_type',
    'positioning.clas.position_uncertainty_x', 'positioning.clas.position_uncertainty_y',
    'positioning.clas.position_uncertainty_z',
    // ISB + Phase Shift (relocated here — PPP-RTK / VRS only)
    'isb', 'inter-system bias', 'phase shift', 'receiver.isb', 'receiver.phase_shift',
    // Adaptive Filter (merged here — PPP-RTK / VRS only)
    'adaptive filter', 'iono forgetting factor', 'iono gain', 'pva forgetting factor',
    'pva gain', 'forgetting factor',
    'adaptive_filter.enabled', 'adaptive_filter.iono_forgetting', 'adaptive_filter.iono_gain',
    'adaptive_filter.pva_forgetting', 'adaptive_filter.pva_gain',
  ],

  receiver: [
    'iono compensation', 'max age', 'baseline length',
    'baseline sigma', 'ignore chi error', 'bds-2 bias', 'ppp sat clock bias', 'ppp sat phase bias',
    'uncorrected bias', 'max bias dt', 'satellite mode', 'reference type', 'signal selection',
    'receiver.iono_correction', 'receiver.max_age',
    'receiver.baseline_length', 'receiver.baseline_sigma', 'receiver.ignore_chi_error',
    'receiver.bds2_bias', 'receiver.ppp_sat_clock_bias', 'receiver.ppp_sat_phase_bias',
    'receiver.uncorr_bias', 'receiver.max_bias_dt', 'receiver.satellite_mode', 'receiver.reference_type',
    'signal_selection.gps', 'signal_selection.qzs', 'signal_selection.galileo',
  ],

  antenna: [
    'rover position', 'base position', 'position type', 'lat lon height', 'ecef', 'xyz',
    'antenna type', 'antenna name', 'antenna delta', 'delta-e', 'delta-n', 'delta-u',
    'max avg epochs', 'init reset', 'station position file', 'station pos',
    'antenna.rover.mode', 'antenna.rover.values', 'antenna.rover.antenna_type',
    'antenna.rover.antenna_delta', 'antenna.base.mode', 'antenna.base.values',
    'antenna.base.antenna_type', 'antenna.base.antenna_delta', 'files.station_pos',
  ],

  format: [
    'solution format', 'output header', 'processing options', 'velocity', 'time format',
    'decimals', 'lat lon format', 'field separator', 'datum', 'height', 'geoid model',
    'static solution mode', 'single on outage', 'nmea rmc gga', 'nmea gsa gsv',
    'solution status', 'debug trace', 'trace level',
    'output.solution_format', 'output.output_header', 'output.output_processing_options',
    'output.output_velocity', 'output.time_format', 'output.num_decimals', 'output.lat_lon_format',
    'output.field_separator', 'output.datum', 'output.height', 'output.geoid_model',
    'output.static_solution_mode', 'output.output_single_on_outage', 'output.output_solution_status',
    'output.debug_trace',
  ],

  files: [
    'satellite antenna pcv file', 'receiver antenna pcv file', 'atx', 'geoid data file',
    'dcb data file', 'eop data file', 'ocean loading file', 'blq', 'ionosphere data file',
    'elevation mask file', 'fcb file', 'bias sinex file', 'cssr grid file', 'isb table file',
    'phase cycle file',
    'files.satellite_atx', 'files.receiver_atx', 'files.geoid', 'files.dcb', 'files.eop',
    'files.ocean_loading', 'files.ionosphere', 'files.elevation_mask_file', 'files.fcb',
    'files.bias_sinex', 'files.cssr_grid', 'files.isb_table', 'files.phase_cycle',
  ],

  server: [
    'base interpolation', 'time interpolation', 'sbas satellite', 'rinex option', 'ppp option',
    'rtcm option', 'l6 margin', 'rtkrcv',
    'server.time_interpolation', 'server.sbas_satellite', 'server.rinex_option_1',
    'server.rinex_option_2', 'server.ppp_option', 'server.rtcm_option', 'server.l6_margin',
  ],
};

/** Precomputed lowercased search text per section (labels + TOML keys joined). */
export const SECTION_SEARCH_TEXT: Record<string, string> = Object.fromEntries(
  Object.entries(SECTION_SEARCH).map(([section, terms]) => [section, terms.join(' ').toLowerCase()]),
);
