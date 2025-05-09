import "katex/dist/katex.min.css";
import ReactLatex from "react-latex-next";

const Latex = ({ children }: { children?: string }) => {
  return children && <ReactLatex>{children}</ReactLatex>;
};

export default Latex;
