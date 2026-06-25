"use client";

import { useEffect } from "react";
import Placeholder from "@tiptap/extension-placeholder";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  Bold,
  Heading2,
  Heading3,
  Italic,
  List,
  ListOrdered,
} from "lucide-react";

import { Button } from "@/components/ui/button";

interface TipTapEditorProps {
  content: string;
  onChange: (html: string) => void;
  editable: boolean;
}

function Toolbar({ editor }: { editor: Editor }) {
  const btnClass = (active: boolean) =>
    `h-8 w-8 p-0 transition-all duration-200 ${
      active
        ? "bg-primary/15 text-primary shadow-sm ring-1 ring-primary/20"
        : "text-muted-foreground hover:bg-muted hover:text-foreground"
    }`;

  return (
    <div className="flex flex-wrap gap-1.5 border-b border-border/50 bg-muted/20 backdrop-blur-md p-2.5 rounded-t-xl">
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("bold"))} onClick={() => editor.chain().focus().toggleBold().run()}>
        <Bold className="h-4 w-4" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("italic"))} onClick={() => editor.chain().focus().toggleItalic().run()}>
        <Italic className="h-4 w-4" />
      </Button>
      <div className="w-px h-6 bg-border/50 mx-1 self-center"></div>
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("heading", { level: 2 }))} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}>
        <Heading2 className="h-4 w-4" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("heading", { level: 3 }))} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}>
        <Heading3 className="h-4 w-4" />
      </Button>
      <div className="w-px h-6 bg-border/50 mx-1 self-center"></div>
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("bulletList"))} onClick={() => editor.chain().focus().toggleBulletList().run()}>
        <List className="h-4 w-4" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btnClass(editor.isActive("orderedList"))} onClick={() => editor.chain().focus().toggleOrderedList().run()}>
        <ListOrdered className="h-4 w-4" />
      </Button>
    </div>
  );
}

export default function TipTapEditor({ content, onChange, editable }: TipTapEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: "اینجا محل تولد محتوای شماست...",
      }),
    ],
    content,
    editable,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class: "tiptap min-h-[400px] p-6 text-right focus:outline-none",
      },
    },
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getHTML());
    },
  });

  useEffect(() => {
    if (!editor) return;
    if (content !== editor.getHTML()) {
      editor.commands.setContent(content, { emitUpdate: false });
    }
  }, [content, editor]);

  useEffect(() => {
    if (editor) {
      editor.setEditable(editable);
    }
  }, [editable, editor]);

  if (!editor) {
    return (
      <div className="flex h-[400px] items-center justify-center rounded-xl border border-border/50 bg-card/50 text-muted-foreground/70 animate-pulse">
        در حال آماده‌سازی ادیتور...
      </div>
    );
  }

  return (
    <div dir="rtl" className="overflow-hidden rounded-xl border border-border/60 bg-card/40 backdrop-blur-sm shadow-sm transition-all focus-within:border-primary/50 focus-within:shadow-md focus-within:shadow-primary/10">
      {editable && <Toolbar editor={editor} />}
      <EditorContent editor={editor} />
    </div>
  );
}