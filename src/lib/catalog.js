import categories from '../data/categories.json';
import products from '../data/products.json';

export const PLACEHOLDER_IMAGE = '/images/placeholder.svg';

export { categories, products };

export function getCategory(slug) {
  return categories.find((c) => c.slug === slug);
}

export function productsInCategory(slug) {
  return products.filter((p) => p.category === slug);
}

export function mainImage(product) {
  return product.images?.[0] ?? PLACEHOLDER_IMAGE;
}
