export const CATS = [
  'Home', 'World', 'Politics', 'Business', 'Tech', 'Health', 'Science', 
  'Entertainment', 'Events', 'Sports', 'Surveys', 'Polls'
];

export const CAT_LOGOS = {
  home: 'https://images.unsplash.com/photo-1504711434969-e33886168d6c?w=400&q=80',
  world: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&q=80',
  politics: 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=400&q=80',
  business: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80',
  tech: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&q=80',
  health: 'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&q=80',
  science: 'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=400&q=80',
  entertainment: 'https://images.unsplash.com/photo-1603190287605-e6ade32fa852?w=400&q=80',
  events: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=400&q=80',
  sports: 'https://images.unsplash.com/photo-1461896836934-bd45ba6b0e28?w=400&q=80',
  surveys: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&q=80',
  polls: 'https://images.unsplash.com/photo-1540910419892-4a39d20b2944?w=400&q=80',
};

export const getImg = (u, c) => {
  if (!u) return CAT_LOGOS[(c||'').toLowerCase().trim()] || CAT_LOGOS.home;
  if (u.startsWith('/uploads')) {
    const base = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '');
    return `${base}${u}`;
  }
  return u;
};
