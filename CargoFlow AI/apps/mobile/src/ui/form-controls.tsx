import { Text, TextInput, TextInputProps, TouchableOpacity, View, StyleSheet } from 'react-native';

import { theme } from '../theme/tokens';

type FieldProps = TextInputProps & {
  label: string;
  hint?: string;
};

export function Field({ label, hint, style, ...props }: FieldProps) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor="#7b7f77"
        style={[styles.input, style]}
        {...props}
      />
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

type PillButtonProps = {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
};

export function PillButton({ label, onPress, variant = 'primary', disabled = false }: PillButtonProps) {
  const secondary = variant === 'secondary';

  return (
    <TouchableOpacity
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={[
        styles.button,
        secondary ? styles.buttonSecondary : styles.buttonPrimary,
        disabled ? styles.buttonDisabled : null,
      ]}
    >
      <Text style={[styles.buttonText, secondary ? styles.buttonTextSecondary : null]}>{label}</Text>
    </TouchableOpacity>
  );
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.sectionTitleWrap}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  fieldWrap: {
    gap: 8,
  },
  label: {
    fontFamily: theme.font.body,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    color: theme.colors.muted,
  },
  input: {
    borderRadius: theme.radius.sm,
    borderWidth: 1,
    borderColor: theme.colors.line,
    backgroundColor: '#fffdf8',
    paddingHorizontal: 14,
    paddingVertical: 13,
    color: theme.colors.ink,
    fontFamily: theme.font.body,
    fontSize: 16,
  },
  hint: {
    fontFamily: theme.font.body,
    color: theme.colors.muted,
    fontSize: 12,
    lineHeight: 18,
  },
  button: {
    borderRadius: 999,
    paddingHorizontal: 18,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 50,
  },
  buttonPrimary: {
    backgroundColor: theme.colors.ember,
  },
  buttonSecondary: {
    backgroundColor: '#fffaf0',
    borderWidth: 1,
    borderColor: theme.colors.line,
  },
  buttonDisabled: {
    opacity: 0.55,
  },
  buttonText: {
    fontFamily: theme.font.heading,
    color: '#fff6eb',
    fontSize: 17,
  },
  buttonTextSecondary: {
    color: theme.colors.ink,
  },
  sectionTitleWrap: {
    gap: 6,
  },
  sectionTitle: {
    fontFamily: theme.font.heading,
    fontSize: 28,
    color: theme.colors.ink,
  },
  sectionSubtitle: {
    fontFamily: theme.font.body,
    color: theme.colors.muted,
    fontSize: 15,
    lineHeight: 22,
  },
});
