import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { theme } from '../theme/tokens';

export function BootstrapScreen() {
  return (
    <View style={styles.screen}>
      <View style={styles.card}>
        <ActivityIndicator color={theme.colors.ember} size="large" />
        <Text style={styles.title}>Ripristino sessione</Text>
        <Text style={styles.subtitle}>
          Verifico token locale e profilo backend prima di aprire la dashboard.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.paper,
    padding: 20,
  },
  card: {
    width: '100%',
    maxWidth: 460,
    backgroundColor: theme.colors.card,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.line,
    padding: 24,
    gap: 14,
    alignItems: 'center',
  },
  title: {
    fontFamily: theme.font.heading,
    fontSize: 28,
    color: theme.colors.ink,
  },
  subtitle: {
    fontFamily: theme.font.body,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.muted,
    textAlign: 'center',
  },
});
