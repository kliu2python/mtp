import { API_URL } from '../constants';

export const buildFileUrl = (path) => {
  if (!path) return '';
  const base = API_URL?.replace(/\/$/, '') || '';
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};

export const buildAcceptableDetailPath = (platformKey, recordId) =>
  `/preflight/acceptable/${platformKey}/${recordId}`;

export const normalizeAcceptableRecords = (records = []) =>
  records.reduce(
    (acc, record) => {
      const params = record.build_parameters || {};
      const platformKey = (record.platform || '').toLowerCase().includes('ios') ? 'ios' : 'android';
      const mantisIds = record.resolved_mantis_ids || record.mantis_ids || params.mantis_ids || [];
      const mantisEntries = Array.isArray(mantisIds)
        ? mantisIds.map((id) => ({
            value: id,
            label: `#${id}`,
            url: `https://mantis.fortinet.com/bug_view_page.php?bug_id=${id}`,
          }))
        : [];

      const buildNumber =
        record.build_number ||
        params.build_number ||
        params.buildNumber ||
        params.build ||
        params.build_num ||
        record.started_at ||
        'N/A';
      const downloadUrl = record.download_url || params.app_download_url || params.download_url;
      const fileName =
        record.app_file ||
        params.ftm_ipa_version ||
        params.ftm_apk_version ||
        params.ftm_ipa ||
        params.ftm_apk ||
        params.ftm_build_version ||
        params.ftm_build ||
        record.name ||
        'N/A';
      const rawId = record._id?.$oid || record._id;
      const recordId = rawId || record.name || `${platformKey}-${record.build_url || Date.now()}`;

      const entry = {
        id: recordId,
        rawId,
        name: record.name,
        platform: platformKey,
        fileName,
        buildNumber,
        mantis: mantisEntries,
        downloadUrl,
        jenkinsUrl: record.build_url,
        status: (record.res || record.status || 'RUNNING').toString().toUpperCase(),
        detailPath: buildAcceptableDetailPath(platformKey, recordId),
        createdAt: record.created_at || record.started_at || record.timestamp,
      };

      acc[platformKey] = [...acc[platformKey], entry];
      return acc;
    },
    { ios: [], android: [] },
  );

