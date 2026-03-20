import { View, Text, StyleSheet } from 'react-native';

import { theme } from '../theme/tokens';

type RolePanelProps = {
  eyebrow: string;
  title: string;
  bullets: string[];
  accent: string;
};

export function RolePanel({ eyebrow, title, bullets, accent }: RolePanelProps) {
  return (
    <View style={[styles.card, { borderColor: accent }]}> 
      <Text style={[styles.eyebrow, { color: accent }]}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
      <View style={styles.list}>
        {bullets.map((item) => (
          <View key={item} style={styles.listRow}>
            <View style={[styles.dot, { backgroundColor: accent }]} />
            <Text style={styles.item}>{item}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.card,
    borderWidth: 1,
    borderRadius: theme.radius.md,
    padding: 20,
    gap: 10,
  },
  eyebrow: {
    fontFamily: theme.font.body,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 2,
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 24,
    color: theme.colors.ink,
  },
  list: {
    gap: 10,
    marginTop: 4,
  },
  listRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 999,
    marginTop: 7,
  },
  item: {
    flex: 1,
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.muted,
  },
});
