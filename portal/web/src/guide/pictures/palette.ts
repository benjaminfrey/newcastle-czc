import { useTheme } from "@mui/material/styles";
import type { PicturePalette } from "../theme/tokens";

// The pictures' colours, from the theme (guided plan 5): nothing under pictures/ names a colour.
export function usePicturePalette(): PicturePalette {
  return useTheme().guide.picture;
}
