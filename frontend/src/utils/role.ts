export const getRoleDisplayName = (role?: string | null): string => {
  if (role === 'admin') return 'Administrateur'
  if (role === 'tester') return 'Ingénieur QA'
  return role || 'Utilisateur'
}
