import { StyleSheet, Text, View } from 'react-native';

import { MetricCardModel, TimelineItemModel } from '../app/dashboard-data';
import { theme } from '../theme/tokens';

export function MetricCard({ item }: { item: MetricCardModel }) {
  const toneColor = getToneColor(item.tone);

  return (
    <View style={[styles.metricCard, { borderColor: toneColor }]}> 
      <Text style={[styles.metricLabel, { color: toneColor }]}>{item.label}</Text>
      <Text style={styles.metricValue}>{item.value}</Text>
    </View>
  );
}

export function TimelineCard({ item }: { item: TimelineItemModel }) {
  const accent = getStatusColor(item.status);

  return (
    <View style={styles.timelineCard}>
      <View style={styles.timelineHeader}>
        <View style={[styles.timelineDot, { backgroundColor: accent }]} />
        <Text style={styles.timelineTitle}>{item.title}</Text>
      </View>
      <Text style={styles.timelineSubtitle}>{item.subtitle}</Text>
      <Text style={styles.timelineMeta}>{item.meta}</Text>
    </View>
  );
}

function getToneColor(tone: MetricCardModel['tone']) {
  if (tone === 'pine') {
    return theme.colors.pine;
  }
  if (tone === 'sky') {
    return '#4f8f8a';
  }
  return theme.colors.ember;
}

function getStatusColor(status: TimelineItemModel['status']) {
  if (status === 'live') {
    return theme.colors.ember;
  }
  if (status === 'attention') {
    return '#cf7a31';
  }
  return theme.colors.pine;
}

const styles = StyleSheet.create({
  metricCard: {
    flex: 1,
    minWidth: 120,
    backgroundColor: '#fffaf0',
    borderRadius: theme.radius.md,
    borderWidth: 1,
    padding: 16,
    gap: 8,
  },
  metricLabel: {
    fontFamily: theme.font.body,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1.4,
  },
  metricValue: {
    fontFamily: theme.font.heading,
    fontSize: 32,
    color: theme.colors.ink,
  },
  timelineCard: {
    backgroundColor: '#fffdf8',
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 16,
    gap: 8,
  },
  timelineHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  timelineDot: {
    width: 10,
    height: 10,
    borderRadius: 999,
  },
  timelineTitle: {
    flex: 1,
    fontFamily: theme.font.heading,
    fontSize: 21,
    color: theme.colors.ink,
  },
  timelineSubtitle: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.ink,
  },
  timelineMeta: {
    fontFamily: theme.font.body,
    fontSize: 14,
    lineHeight: 20,
    color: theme.colors.muted,
  },
});
