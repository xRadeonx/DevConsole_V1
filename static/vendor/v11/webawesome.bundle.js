(()=>{var Xt=globalThis,Kt=Xt.ShadowRoot&&(Xt.ShadyCSS===void 0||Xt.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,he=Symbol(),De=new WeakMap,Pt=class{constructor(t,o,r){if(this._$cssResult$=!0,r!==he)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=o}get styleSheet(){let t=this.o,o=this.t;if(Kt&&t===void 0){let r=o!==void 0&&o.length===1;r&&(t=De.get(o)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&De.set(o,t))}return t}toString(){return this.cssText}},Me=e=>new Pt(typeof e=="string"?e:e+"",void 0,he),T=(e,...t)=>{let o=e.length===1?e[0]:t.reduce((r,i,n)=>r+(s=>{if(s._$cssResult$===!0)return s.cssText;if(typeof s=="number")return s;throw Error("Value passed to 'css' function must be a 'css' function result: "+s+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[n+1],e[0]);return new Pt(o,e,he)},Ne=(e,t)=>{if(Kt)e.adoptedStyleSheets=t.map(o=>o instanceof CSSStyleSheet?o:o.styleSheet);else for(let o of t){let r=document.createElement("style"),i=Xt.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=o.cssText,e.appendChild(r)}},pe=Kt?e=>e:e=>e instanceof CSSStyleSheet?(t=>{let o="";for(let r of t.cssRules)o+=r.cssText;return Me(o)})(e):e;var{is:ar,defineProperty:lr,getOwnPropertyDescriptor:cr,getOwnPropertyNames:dr,getOwnPropertySymbols:hr,getPrototypeOf:pr}=Object,Q=globalThis,Be=Q.trustedTypes,ur=Be?Be.emptyScript:"",fr=Q.reactiveElementPolyfillSupport,Ot=(e,t)=>e,Rt={toAttribute(e,t){switch(t){case Boolean:e=e?ur:null;break;case Object:case Array:e=e==null?e:JSON.stringify(e)}return e},fromAttribute(e,t){let o=e;switch(t){case Boolean:o=e!==null;break;case Number:o=e===null?null:Number(e);break;case Object:case Array:try{o=JSON.parse(e)}catch{o=null}}return o}},Gt=(e,t)=>!ar(e,t),ze={attribute:!0,type:String,converter:Rt,reflect:!1,useDefault:!1,hasChanged:Gt};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),Q.litPropertyMetadata??(Q.litPropertyMetadata=new WeakMap);var j=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,o=ze){if(o.state&&(o.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((o=Object.create(o)).wrapped=!0),this.elementProperties.set(t,o),!o.noAccessor){let r=Symbol(),i=this.getPropertyDescriptor(t,r,o);i!==void 0&&lr(this.prototype,t,i)}}static getPropertyDescriptor(t,o,r){let{get:i,set:n}=cr(this.prototype,t)??{get(){return this[o]},set(s){this[o]=s}};return{get:i,set(s){let l=i?.call(this);n?.call(this,s),this.requestUpdate(t,l,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ze}static _$Ei(){if(this.hasOwnProperty(Ot("elementProperties")))return;let t=pr(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(Ot("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(Ot("properties"))){let o=this.properties,r=[...dr(o),...hr(o)];for(let i of r)this.createProperty(i,o[i])}let t=this[Symbol.metadata];if(t!==null){let o=litPropertyMetadata.get(t);if(o!==void 0)for(let[r,i]of o)this.elementProperties.set(r,i)}this._$Eh=new Map;for(let[o,r]of this.elementProperties){let i=this._$Eu(o,r);i!==void 0&&this._$Eh.set(i,o)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let o=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let i of r)o.unshift(pe(i))}else t!==void 0&&o.push(pe(t));return o}static _$Eu(t,o){let r=o.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,o=this.constructor.elementProperties;for(let r of o.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ne(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,o,r){this._$AK(t,r)}_$ET(t,o){let r=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,r);if(i!==void 0&&r.reflect===!0){let n=(r.converter?.toAttribute!==void 0?r.converter:Rt).toAttribute(o,r.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,o){let r=this.constructor,i=r._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let n=r.getPropertyOptions(i),s=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:Rt;this._$Em=i;let l=s.fromAttribute(o,n.type);this[i]=l??this._$Ej?.get(i)??l,this._$Em=null}}requestUpdate(t,o,r,i=!1,n){if(t!==void 0){let s=this.constructor;if(i===!1&&(n=this[t]),r??(r=s.getPropertyOptions(t)),!((r.hasChanged??Gt)(n,o)||r.useDefault&&r.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(s._$Eu(t,r))))return;this.C(t,o,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,o,{useDefault:r,reflect:i,wrapped:n},s){r&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,s??o??this[t]),n!==!0||s!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(o=void 0),this._$AL.set(t,o)),i===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(o){Promise.reject(o)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[i,n]of r){let{wrapped:s}=n,l=this[i];s!==!0||this._$AL.has(i)||l===void 0||this.C(i,void 0,n,l)}}let t=!1,o=this._$AL;try{t=this.shouldUpdate(o),t?(this.willUpdate(o),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(o)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(o)}willUpdate(t){}_$AE(t){this._$EO?.forEach(o=>o.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(o=>this._$ET(o,this[o]))),this._$EM()}updated(t){}firstUpdated(t){}};j.elementStyles=[],j.shadowRootOptions={mode:"open"},j[Ot("elementProperties")]=new Map,j[Ot("finalized")]=new Map,fr?.({ReactiveElement:j}),(Q.reactiveElementVersions??(Q.reactiveElementVersions=[])).push("2.1.2");var kt=globalThis,Ue=e=>e,Zt=kt.trustedTypes,He=Zt?Zt.createPolicy("lit-html",{createHTML:e=>e}):void 0,je="$lit$",tt=`lit$${Math.random().toFixed(9).slice(2)}$`,Ye="?"+tt,mr=`<${Ye}>`,dt=document,Lt=()=>dt.createComment(""),Dt=e=>e===null||typeof e!="object"&&typeof e!="function",ye=Array.isArray,gr=e=>ye(e)||typeof e?.[Symbol.iterator]=="function",ue=`[ 	
\f\r]`,Tt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Fe=/-->/g,qe=/>/g,lt=RegExp(`>|${ue}(?:([^\\s"'>=/]+)(${ue}*=${ue}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),We=/'/g,Ve=/"/g,Xe=/^(?:script|style|textarea|title)$/i,be=e=>(t,...o)=>({_$litType$:e,strings:t,values:o}),X=be(1),ni=be(2),si=be(3),Y=Symbol.for("lit-noChange"),_=Symbol.for("lit-nothing"),Ie=new WeakMap,ct=dt.createTreeWalker(dt,129);function Ke(e,t){if(!ye(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return He!==void 0?He.createHTML(t):t}var wr=(e,t)=>{let o=e.length-1,r=[],i,n=t===2?"<svg>":t===3?"<math>":"",s=Tt;for(let l=0;l<o;l++){let a=e[l],c,h,d=-1,u=0;for(;u<a.length&&(s.lastIndex=u,h=s.exec(a),h!==null);)u=s.lastIndex,s===Tt?h[1]==="!--"?s=Fe:h[1]!==void 0?s=qe:h[2]!==void 0?(Xe.test(h[2])&&(i=RegExp("</"+h[2],"g")),s=lt):h[3]!==void 0&&(s=lt):s===lt?h[0]===">"?(s=i??Tt,d=-1):h[1]===void 0?d=-2:(d=s.lastIndex-h[2].length,c=h[1],s=h[3]===void 0?lt:h[3]==='"'?Ve:We):s===Ve||s===We?s=lt:s===Fe||s===qe?s=Tt:(s=lt,i=void 0);let p=s===lt&&e[l+1].startsWith("/>")?" ":"";n+=s===Tt?a+mr:d>=0?(r.push(c),a.slice(0,d)+je+a.slice(d)+tt+p):a+tt+(d===-2?l:p)}return[Ke(e,n+(e[o]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},Mt=class e{constructor({strings:t,_$litType$:o},r){let i;this.parts=[];let n=0,s=0,l=t.length-1,a=this.parts,[c,h]=wr(t,o);if(this.el=e.createElement(c,r),ct.currentNode=this.el.content,o===2||o===3){let d=this.el.content.firstChild;d.replaceWith(...d.childNodes)}for(;(i=ct.nextNode())!==null&&a.length<l;){if(i.nodeType===1){if(i.hasAttributes())for(let d of i.getAttributeNames())if(d.endsWith(je)){let u=h[s++],p=i.getAttribute(d).split(tt),f=/([.?@])?(.*)/.exec(u);a.push({type:1,index:n,name:f[2],strings:p,ctor:f[1]==="."?me:f[1]==="?"?ge:f[1]==="@"?we:xt}),i.removeAttribute(d)}else d.startsWith(tt)&&(a.push({type:6,index:n}),i.removeAttribute(d));if(Xe.test(i.tagName)){let d=i.textContent.split(tt),u=d.length-1;if(u>0){i.textContent=Zt?Zt.emptyScript:"";for(let p=0;p<u;p++)i.append(d[p],Lt()),ct.nextNode(),a.push({type:2,index:++n});i.append(d[u],Lt())}}}else if(i.nodeType===8)if(i.data===Ye)a.push({type:2,index:n});else{let d=-1;for(;(d=i.data.indexOf(tt,d+1))!==-1;)a.push({type:7,index:n}),d+=tt.length-1}n++}}static createElement(t,o){let r=dt.createElement("template");return r.innerHTML=t,r}};function bt(e,t,o=e,r){if(t===Y)return t;let i=r!==void 0?o._$Co?.[r]:o._$Cl,n=Dt(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(e),i._$AT(e,o,r)),r!==void 0?(o._$Co??(o._$Co=[]))[r]=i:o._$Cl=i),i!==void 0&&(t=bt(e,i._$AS(e,t.values),i,r)),t}var fe=class{constructor(t,o){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=o}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:o},parts:r}=this._$AD,i=(t?.creationScope??dt).importNode(o,!0);ct.currentNode=i;let n=ct.nextNode(),s=0,l=0,a=r[0];for(;a!==void 0;){if(s===a.index){let c;a.type===2?c=new Nt(n,n.nextSibling,this,t):a.type===1?c=new a.ctor(n,a.name,a.strings,this,t):a.type===6&&(c=new ve(n,this,t)),this._$AV.push(c),a=r[++l]}s!==a?.index&&(n=ct.nextNode(),s++)}return ct.currentNode=dt,i}p(t){let o=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,o),o+=r.strings.length-2):r._$AI(t[o])),o++}},Nt=class e{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,o,r,i){this.type=2,this._$AH=_,this._$AN=void 0,this._$AA=t,this._$AB=o,this._$AM=r,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,o=this._$AM;return o!==void 0&&t?.nodeType===11&&(t=o.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,o=this){t=bt(this,t,o),Dt(t)?t===_||t==null||t===""?(this._$AH!==_&&this._$AR(),this._$AH=_):t!==this._$AH&&t!==Y&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):gr(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==_&&Dt(this._$AH)?this._$AA.nextSibling.data=t:this.T(dt.createTextNode(t)),this._$AH=t}$(t){let{values:o,_$litType$:r}=t,i=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=Mt.createElement(Ke(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===i)this._$AH.p(o);else{let n=new fe(i,this),s=n.u(this.options);n.p(o),this.T(s),this._$AH=n}}_$AC(t){let o=Ie.get(t.strings);return o===void 0&&Ie.set(t.strings,o=new Mt(t)),o}k(t){ye(this._$AH)||(this._$AH=[],this._$AR());let o=this._$AH,r,i=0;for(let n of t)i===o.length?o.push(r=new e(this.O(Lt()),this.O(Lt()),this,this.options)):r=o[i],r._$AI(n),i++;i<o.length&&(this._$AR(r&&r._$AB.nextSibling,i),o.length=i)}_$AR(t=this._$AA.nextSibling,o){for(this._$AP?.(!1,!0,o);t!==this._$AB;){let r=Ue(t).nextSibling;Ue(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},xt=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,o,r,i,n){this.type=1,this._$AH=_,this._$AN=void 0,this.element=t,this.name=o,this._$AM=i,this.options=n,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=_}_$AI(t,o=this,r,i){let n=this.strings,s=!1;if(n===void 0)t=bt(this,t,o,0),s=!Dt(t)||t!==this._$AH&&t!==Y,s&&(this._$AH=t);else{let l=t,a,c;for(t=n[0],a=0;a<n.length-1;a++)c=bt(this,l[r+a],o,a),c===Y&&(c=this._$AH[a]),s||(s=!Dt(c)||c!==this._$AH[a]),c===_?t=_:t!==_&&(t+=(c??"")+n[a+1]),this._$AH[a]=c}s&&!i&&this.j(t)}j(t){t===_?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},me=class extends xt{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===_?void 0:t}},ge=class extends xt{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==_)}},we=class extends xt{constructor(t,o,r,i,n){super(t,o,r,i,n),this.type=5}_$AI(t,o=this){if((t=bt(this,t,o,0)??_)===Y)return;let r=this._$AH,i=t===_&&r!==_||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,n=t!==_&&(r===_||i);i&&this.element.removeEventListener(this.name,this,r),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},ve=class{constructor(t,o,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=o,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){bt(this,t)}};var vr=kt.litHtmlPolyfillSupport;vr?.(Mt,Nt),(kt.litHtmlVersions??(kt.litHtmlVersions=[])).push("3.3.3");var Ge=(e,t,o)=>{let r=o?.renderBefore??t,i=r._$litPart$;if(i===void 0){let n=o?.renderBefore??null;r._$litPart$=i=new Nt(t.insertBefore(Lt(),n),n,void 0,o??{})}return i._$AI(e),i};var Bt=globalThis,et=class extends j{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var o;let t=super.createRenderRoot();return(o=this.renderOptions).renderBefore??(o.renderBefore=t.firstChild),t}update(t){let o=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Ge(o,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Y}};et._$litElement$=!0,et.finalized=!0,Bt.litElementHydrateSupport?.({LitElement:et});var yr=Bt.litElementPolyfillSupport;yr?.({LitElement:et});(Bt.litElementVersions??(Bt.litElementVersions=[])).push("4.2.2");var Ze=T`
  :where(:root),
  .wa-neutral,
  :host([variant='neutral']) {
    --wa-color-fill-loud: var(--wa-color-neutral-fill-loud);
    --wa-color-fill-normal: var(--wa-color-neutral-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-neutral-fill-quiet);
    --wa-color-border-loud: var(--wa-color-neutral-border-loud);
    --wa-color-border-normal: var(--wa-color-neutral-border-normal);
    --wa-color-border-quiet: var(--wa-color-neutral-border-quiet);
    --wa-color-on-loud: var(--wa-color-neutral-on-loud);
    --wa-color-on-normal: var(--wa-color-neutral-on-normal);
    --wa-color-on-quiet: var(--wa-color-neutral-on-quiet);
  }

  .wa-brand,
  :host([variant='brand']) {
    --wa-color-fill-loud: var(--wa-color-brand-fill-loud);
    --wa-color-fill-normal: var(--wa-color-brand-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-brand-fill-quiet);
    --wa-color-border-loud: var(--wa-color-brand-border-loud);
    --wa-color-border-normal: var(--wa-color-brand-border-normal);
    --wa-color-border-quiet: var(--wa-color-brand-border-quiet);
    --wa-color-on-loud: var(--wa-color-brand-on-loud);
    --wa-color-on-normal: var(--wa-color-brand-on-normal);
    --wa-color-on-quiet: var(--wa-color-brand-on-quiet);
  }

  .wa-success,
  :host([variant='success']) {
    --wa-color-fill-loud: var(--wa-color-success-fill-loud);
    --wa-color-fill-normal: var(--wa-color-success-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-success-fill-quiet);
    --wa-color-border-loud: var(--wa-color-success-border-loud);
    --wa-color-border-normal: var(--wa-color-success-border-normal);
    --wa-color-border-quiet: var(--wa-color-success-border-quiet);
    --wa-color-on-loud: var(--wa-color-success-on-loud);
    --wa-color-on-normal: var(--wa-color-success-on-normal);
    --wa-color-on-quiet: var(--wa-color-success-on-quiet);
  }

  .wa-warning,
  :host([variant='warning']) {
    --wa-color-fill-loud: var(--wa-color-warning-fill-loud);
    --wa-color-fill-normal: var(--wa-color-warning-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-warning-fill-quiet);
    --wa-color-border-loud: var(--wa-color-warning-border-loud);
    --wa-color-border-normal: var(--wa-color-warning-border-normal);
    --wa-color-border-quiet: var(--wa-color-warning-border-quiet);
    --wa-color-on-loud: var(--wa-color-warning-on-loud);
    --wa-color-on-normal: var(--wa-color-warning-on-normal);
    --wa-color-on-quiet: var(--wa-color-warning-on-quiet);
  }

  .wa-danger,
  :host([variant='danger']) {
    --wa-color-fill-loud: var(--wa-color-danger-fill-loud);
    --wa-color-fill-normal: var(--wa-color-danger-fill-normal);
    --wa-color-fill-quiet: var(--wa-color-danger-fill-quiet);
    --wa-color-border-loud: var(--wa-color-danger-border-loud);
    --wa-color-border-normal: var(--wa-color-danger-border-normal);
    --wa-color-border-quiet: var(--wa-color-danger-border-quiet);
    --wa-color-on-loud: var(--wa-color-danger-on-loud);
    --wa-color-on-normal: var(--wa-color-danger-on-normal);
    --wa-color-on-quiet: var(--wa-color-danger-on-quiet);
  }
`;var Je=T`
  :host {
    --pulse-color: var(--wa-color-fill-loud, var(--wa-color-brand-fill-loud));

    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.375em 0.625em;
    color: var(--wa-color-on-loud, var(--wa-color-brand-on-loud));
    font-size: max(var(--wa-font-size-3xs), 0.75em);
    font-weight: var(--wa-font-weight-semibold);
    line-height: 1;
    vertical-align: middle;
    white-space: nowrap;
    background-color: var(--wa-color-fill-loud, var(--wa-color-brand-fill-loud));
    border-color: transparent;
    border-radius: var(--wa-border-radius-s);
    border-style: var(--wa-border-style);
    border-width: var(--wa-border-width-s);
    user-select: none;
    -webkit-user-select: none;
    cursor: inherit;

    min-width: 1.25em; /* <-- this is what Safari respects for intrinsic */
    min-height: 1em;
  }

  /* Appearance modifiers */
  :host([appearance='outlined']) {
    --pulse-color: var(--wa-color-border-loud, var(--wa-color-brand-border-loud));

    color: var(--wa-color-on-quiet, var(--wa-color-brand-on-quiet));
    background-color: transparent;
    border-color: var(--wa-color-border-loud, var(--wa-color-brand-border-loud));
  }

  :host([appearance='filled']) {
    --pulse-color: var(--wa-color-fill-normal, var(--wa-color-brand-fill-normal));

    color: var(--wa-color-on-normal, var(--wa-color-brand-on-normal));
    background-color: var(--wa-color-fill-normal, var(--wa-color-brand-fill-normal));
    border-color: transparent;
  }

  :host([appearance='filled-outlined']) {
    --pulse-color: var(--wa-color-border-normal, var(--wa-color-brand-border-normal));

    color: var(--wa-color-on-normal, var(--wa-color-brand-on-normal));
    background-color: var(--wa-color-fill-normal, var(--wa-color-brand-fill-normal));
    border-color: var(--wa-color-border-normal, var(--wa-color-brand-border-normal));
  }

  :host([appearance='accent']) {
    --pulse-color: var(--wa-color-fill-loud, var(--wa-color-brand-fill-loud));

    color: var(--wa-color-on-loud, var(--wa-color-brand-on-loud));
    background-color: var(--wa-color-fill-loud, var(--wa-color-brand-fill-loud));
    border-color: transparent;
  }

  /* Pill modifier */
  :host([pill]) {
    border-radius: var(--wa-border-radius-pill);
  }

  /* Pulse attention */
  :host([attention='pulse']) {
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0% {
      box-shadow: 0 0 0 0 var(--pulse-color);
    }
    70% {
      box-shadow: 0 0 0 0.5rem transparent;
    }
    100% {
      box-shadow: 0 0 0 0 transparent;
    }
  }

  /* Bounce attention */
  :host([attention='bounce']) {
    animation: bounce 1s cubic-bezier(0.28, 0.84, 0.42, 1) infinite;
  }

  @keyframes bounce {
    0%,
    20%,
    50%,
    80%,
    100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-5px);
    }
    60% {
      transform: translateY(-2px);
    }
  }

  /* Prevents vertical space when icons with vertical-align are slotted in - https://github.com/shoelace-style/webawesome/issues/2280 */
  [part='start'],
  [part='end'] {
    line-height: 0;
  }

  slot[name='start']::slotted(*) {
    margin-inline-end: 0.375em;
  }

  slot[name='end']::slotted(*) {
    margin-inline-start: 0.375em;
  }
`;var br=Object.defineProperty,xr=Object.getOwnPropertyDescriptor,Qe=e=>{throw TypeError(e)},m=(e,t,o,r)=>{for(var i=r>1?void 0:r?xr(t,o):t,n=e.length-1,s;n>=0;n--)(s=e[n])&&(i=(r?s(t,o,i):s(i))||i);return r&&i&&br(t,o,i),i},to=(e,t,o)=>t.has(e)||Qe("Cannot "+o),eo=(e,t,o)=>(to(e,t,"read from private field"),o?o.call(e):t.get(e)),oo=(e,t,o)=>t.has(e)?Qe("Cannot add the same private member more than once"):t instanceof WeakSet?t.add(e):t.set(e,o),ro=(e,t,o,r)=>(to(e,t,"write to private field"),r?r.call(e,o):t.set(e,o),o);var ot=e=>(t,o)=>{o!==void 0?o.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)};var Ar={attribute:!0,type:String,converter:Rt,reflect:!1,hasChanged:Gt},$r=(e=Ar,t,o)=>{let{kind:r,metadata:i}=o,n=globalThis.litPropertyMetadata.get(i);if(n===void 0&&globalThis.litPropertyMetadata.set(i,n=new Map),r==="setter"&&((e=Object.create(e)).wrapped=!0),n.set(o.name,e),r==="accessor"){let{name:s}=o;return{set(l){let a=t.get.call(this);t.set.call(this,l),this.requestUpdate(s,a,e,!0,l)},init(l){return l!==void 0&&this.C(s,void 0,e,l),l}}}if(r==="setter"){let{name:s}=o;return function(l){let a=this[s];t.call(this,l),this.requestUpdate(s,a,e,!0,l)}}throw Error("Unsupported decorator location: "+r)};function g(e){return(t,o)=>typeof o=="object"?$r(e,t,o):((r,i,n)=>{let s=i.hasOwnProperty(n);return i.constructor.createProperty(n,r),s?Object.getOwnPropertyDescriptor(i,n):void 0})(e,t,o)}function io(e){return g({...e,state:!0,attribute:!1})}var ht=(e,t,o)=>(o.configurable=!0,o.enumerable=!0,Reflect.decorate&&typeof t!="object"&&Object.defineProperty(e,t,o),o);function pt(e,t){return(o,r,i)=>{let n=s=>s.renderRoot?.querySelector(e)??null;if(t){let{get:s,set:l}=typeof r=="object"?o:i??(()=>{let a=Symbol();return{get(){return this[a]},set(c){this[a]=c}}})();return ht(o,r,{get(){let a=s.call(this);return a===void 0&&(a=n(this),(a!==null||this.hasUpdated)&&l.call(this,a)),a}})}return ht(o,r,{get(){return n(this)}})}}var Sr=T`
  :host {
    box-sizing: border-box;
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit;
  }

  [hidden],
  :host([hidden]) {
    display: none !important;
  }
`,_r=/;\s+$/;function Cr(e){return e.replace(/[A-Z]/g,t=>`-${t.toLowerCase()}`)}function no(e){let{property:t,value:o,element:r}=e;if(o){let i=r.getAttribute("style")||"";i&&(i.match(_r)||(i+=";"),i+=" ");let n=`${t}: ${o}`;return i.includes(n)?void 0:`${i}${n};`}return null}var Jt,M=class extends et{constructor(){super(),oo(this,Jt,!1),this.initialReflectedProperties=new Map,this.didSSR=!!this.shadowRoot,this.customStates={set:(t,o)=>{if(this.internals?.states)try{o?this.internals.states.add(t):this.internals.states.delete(t)}catch(r){if(String(r).includes("must start with '--'"))console.error("Your browser implements an outdated version of CustomStateSet. Consider using a polyfill");else throw r}},has:t=>{if(!this.internals?.states)return!1;try{return this.internals.states.has(t)}catch{return!1}}};try{this.internals=this.attachInternals()}catch{console.error("Element internals are not supported in your browser. Consider using a polyfill")}this.customStates.set("wa-defined",!0);let e=this.constructor;for(let[t,o]of e.elementProperties)o.default==="inherit"&&o.initial!==void 0&&typeof t=="string"&&this.customStates.set(`initial-${t}-${o.initial}`,!0)}static get styles(){let e=Array.isArray(this.css)?this.css:this.css?[this.css]:[];return[Sr,...e]}connectedCallback(){super.connectedCallback(),this.didSSR||this.shadowRoot?.prepend(document.createComment(` Web Awesome: https://webawesome.com/docs/components/${this.localName.replace("wa-","")} `)),this.didSSR&&this.updateComplete.then(()=>{this.shadowRoot?.prepend(document.createComment(` Web Awesome: https://webawesome.com/docs/components/${this.localName.replace("wa-","")} `))})}attributeChangedCallback(e,t,o){eo(this,Jt)||(this.constructor.elementProperties.forEach((r,i)=>{r.reflect&&this[i]!=null&&this.initialReflectedProperties.set(i,this[i])}),ro(this,Jt,!0)),super.attributeChangedCallback(e,t,o)}willUpdate(e){super.willUpdate(e),this.initialReflectedProperties.forEach((t,o)=>{e.has(o)&&this[o]==null&&(this[o]=t)})}firstUpdated(e){super.firstUpdated(e),this.didSSR&&this.shadowRoot?.querySelectorAll("slot").forEach(t=>{t.dispatchEvent(new Event("slotchange",{bubbles:!0,composed:!1,cancelable:!1}))})}update(e){try{super.update(e)}catch(t){if(this.didSSR&&!this.hasUpdated){let o=new Event("lit-hydration-error",{bubbles:!0,composed:!0,cancelable:!1});o.error=t,this.dispatchEvent(o)}throw t}}setStyle(e,t){if(!this.style){let o=no({property:Cr(e),value:t,element:this});o&&this.setAttribute("style",o);return}this.style[e]=t}setStyleProperty(e,t){if(!this.style){let o=no({property:e,value:t,element:this});o&&this.setAttribute("style",o);return}this.style.setProperty(e,t)}relayNativeEvent(e,t){e.stopImmediatePropagation(),this.dispatchEvent(new e.constructor(e.type,{...e,...t}))}};Jt=new WeakMap;m([g()],M.prototype,"dir",2);m([g()],M.prototype,"lang",2);m([g({type:Boolean,reflect:!0,attribute:"did-ssr"})],M.prototype,"didSSR",2);var rt=class extends M{constructor(){super(...arguments),this.variant="brand",this.appearance="accent",this.pill=!1,this.attention="none"}render(){return X`
      <span part="start">
        <slot name="start"></slot>
      </span>

      <span part="base badge" role="status">
        <slot></slot>
      </span>

      <span part="end">
        <slot name="end"></slot>
      </span>
    `}};rt.css=[Ze,Je];m([g({reflect:!0})],rt.prototype,"variant",2);m([g({reflect:!0})],rt.prototype,"appearance",2);m([g({type:Boolean,reflect:!0})],rt.prototype,"pill",2);m([g({reflect:!0})],rt.prototype,"attention",2);rt=m([ot("wa-badge")],rt);var so=T`
  :host {
    --max-width: 30ch;

    /** These styles are added so we don't interfere in the DOM. */
    display: inline-block;
    position: absolute;

    /** Defaults for inherited CSS properties */
    color: var(--wa-tooltip-content-color);
    font-size: var(--wa-tooltip-font-size);
    line-height: var(--wa-tooltip-line-height);
    text-align: start;
    white-space: normal;
  }

  .tooltip {
    --arrow-size: var(--wa-tooltip-arrow-size);
    --arrow-color: var(--wa-tooltip-background-color);
  }

  .tooltip::part(popup) {
    z-index: 1000;
  }

  .tooltip[placement^='top']::part(popup) {
    transform-origin: bottom;
  }

  .tooltip[placement^='bottom']::part(popup) {
    transform-origin: top;
  }

  .tooltip[placement^='left']::part(popup) {
    transform-origin: right;
  }

  .tooltip[placement^='right']::part(popup) {
    transform-origin: left;
  }

  .body {
    display: block;
    width: max-content;
    max-width: var(--max-width);
    border-radius: var(--wa-tooltip-border-radius);
    background-color: var(--wa-tooltip-background-color);
    border: var(--wa-tooltip-border-width) var(--wa-tooltip-border-style) var(--wa-tooltip-border-color);
    padding: 0.25em 0.5em;
    user-select: none;
    -webkit-user-select: none;
  }

  .tooltip {
    --popup-border-width: var(--wa-tooltip-border-width);

    /* Inset box-shadow, not a border: Safari seams a clip-path edge that runs along a border. */
    &::part(arrow) {
      box-shadow: inset calc(-1 * var(--wa-tooltip-border-width)) calc(-1 * var(--wa-tooltip-border-width)) 0 0
        var(--wa-tooltip-border-color);
    }
  }
`;var ao=class extends Event{constructor(){super("wa-show",{bubbles:!0,cancelable:!0,composed:!0})}};var lo=class extends Event{constructor(e){super("wa-hide",{bubbles:!0,cancelable:!0,composed:!0}),this.detail=e}};var co=class extends Event{constructor(){super("wa-after-hide",{bubbles:!0,cancelable:!1,composed:!0})}};var ho=class extends Event{constructor(){super("wa-after-show",{bubbles:!0,cancelable:!1,composed:!0})}};var po=class extends Event{constructor(){super("wa-reposition",{bubbles:!0,cancelable:!1,composed:!0})}};var uo=T`
  :host {
    --arrow-color: black;
    --arrow-size: var(--wa-tooltip-arrow-size);
    --popup-border-width: 0px;
    --show-duration: var(--wa-transition-fast);
    --hide-duration: var(--wa-transition-fast);

    /*
     * These properties are computed to account for the arrow's dimensions after being rotated 45º. The constant
     * 0.7071 is derived from sin(45) to calculate the length of the arrow after rotation.
     *
     * The diamond will be translated inward by --arrow-base-offset, the border thickness, to centralise it on
     * the inner edge of the popup border. This also means we need to increase the size of the arrow by the
     * same amount to compensate.
     *
     * A diamond shaped clipping mask is used to avoid overlap of popup content. This extends slightly inward so
     * the popup border is covered with no sub-pixel rounding artifacts. The diamond corners are mitred at 22.5º
     * to properly merge any arrow border with the popup border. The constant 1.4142 is derived from 1 + tan(22.5).
     *
     */
    --arrow-base-offset: var(--popup-border-width);
    --arrow-size-diagonal: calc((var(--arrow-size) + var(--arrow-base-offset)) * 0.7071);
    --arrow-padding-offset: calc(var(--arrow-size-diagonal) - var(--arrow-size));
    --arrow-size-div: calc(var(--arrow-size-diagonal) * 2);
    --arrow-clipping-corner: calc(var(--arrow-base-offset) * 1.4142);

    display: contents;
  }

  .popup {
    position: absolute;
    isolation: isolate;
    max-width: var(--auto-size-available-width, none);
    max-height: var(--auto-size-available-height, none);

    /* Clear UA styles for [popover] */
    :where(&) {
      inset: unset;
      padding: unset;
      margin: unset;
      width: unset;
      height: unset;
      color: unset;
      background: unset;
      border: unset;
      overflow: unset;
    }
  }

  .popup-fixed {
    position: fixed;
  }

  .popup:not(.popup-active) {
    display: none;
  }

  .arrow {
    position: absolute;
    width: var(--arrow-size-div);
    height: var(--arrow-size-div);
    background: var(--arrow-color);
    z-index: 3;
    clip-path: polygon(
      var(--arrow-clipping-corner) 100%,
      var(--arrow-base-offset) calc(100% - var(--arrow-base-offset)),
      calc(var(--arrow-base-offset) - 2px) calc(100% - var(--arrow-base-offset)),
      calc(100% - var(--arrow-base-offset)) calc(var(--arrow-base-offset) - 2px),
      calc(100% - var(--arrow-base-offset)) var(--arrow-base-offset),
      100% var(--arrow-clipping-corner),
      100% 100%
    );
    rotate: 45deg;
  }

  :host([data-current-placement|='left']) .arrow {
    rotate: -45deg;
  }

  :host([data-current-placement|='right']) .arrow {
    rotate: 135deg;
  }

  :host([data-current-placement|='bottom']) .arrow {
    rotate: 225deg;
  }

  /* Hover bridge */
  .popup-hover-bridge:not(.popup-hover-bridge-visible) {
    display: none;
  }

  .popup-hover-bridge {
    position: fixed;
    z-index: 899;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    clip-path: polygon(
      var(--hover-bridge-top-left-x, 0) var(--hover-bridge-top-left-y, 0),
      var(--hover-bridge-top-right-x, 0) var(--hover-bridge-top-right-y, 0),
      var(--hover-bridge-bottom-right-x, 0) var(--hover-bridge-bottom-right-y, 0),
      var(--hover-bridge-bottom-left-x, 0) var(--hover-bridge-bottom-left-y, 0)
    );
  }

  /* Built-in animations */
  .show {
    animation: show var(--show-duration) ease;
  }

  .hide {
    animation: show var(--hide-duration) ease reverse;
  }

  @keyframes show {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .show-with-scale {
    animation: show-with-scale var(--show-duration) ease;
  }

  .hide-with-scale {
    animation: show-with-scale var(--hide-duration) ease reverse;
  }

  @keyframes show-with-scale {
    from {
      opacity: 0;
      scale: 0.8;
    }
    to {
      opacity: 1;
      scale: 1;
    }
  }
`;var xe=new Set,At=new Map,K,Ae="ltr",$e="en",fo=typeof MutationObserver<"u"&&typeof document<"u"&&typeof document.documentElement<"u";if(fo){let e=new MutationObserver(mo);Ae=document.documentElement.dir||"ltr",$e=document.documentElement.lang||navigator.language,e.observe(document.documentElement,{attributes:!0,attributeFilter:["dir","lang"]})}function zt(...e){e.map(t=>{let o=t.$code.toLowerCase();At.has(o)?At.set(o,Object.assign(Object.assign({},At.get(o)),t)):At.set(o,t),K||(K=t)}),mo()}function mo(){fo&&(Ae=document.documentElement.dir||"ltr",$e=document.documentElement.lang||navigator.language),[...xe.keys()].map(e=>{typeof e.requestUpdate=="function"&&e.requestUpdate()})}var Qt=class{constructor(t){this.host=t,this.host.addController(this)}hostConnected(){xe.add(this.host)}hostDisconnected(){xe.delete(this.host)}dir(){return`${this.host.dir||Ae}`.toLowerCase()}lang(){let t=`${this.host.lang||$e}`.toLowerCase().replace(/_/g,"-");try{return new Intl.Locale(t),t}catch{return K?K.$code.toLowerCase():"en"}}getTranslationData(t){var o,r;let i;try{i=new Intl.Locale(t.replace(/_/g,"-"))}catch{return{locale:void 0,language:"",region:"",primary:void 0,secondary:void 0}}let n=i.language.toLowerCase(),s=(r=(o=i.region)===null||o===void 0?void 0:o.toLowerCase())!==null&&r!==void 0?r:"",l=At.get(`${n}-${s}`),a=At.get(n);return{locale:i,language:n,region:s,primary:l,secondary:a}}exists(t,o){var r;let{primary:i,secondary:n}=this.getTranslationData((r=o.lang)!==null&&r!==void 0?r:this.lang());return o=Object.assign({includeFallback:!1},o),!!(i&&i[t]||n&&n[t]||o.includeFallback&&K&&K[t])}term(t,...o){let{primary:r,secondary:i}=this.getTranslationData(this.lang()),n;if(r&&r[t])n=r[t];else if(i&&i[t])n=i[t];else if(K&&K[t])n=K[t];else return console.error(`No translation found for: ${String(t)}`),String(t);return typeof n=="function"?n(...o):n}date(t,o){return t=new Date(t),new Intl.DateTimeFormat(this.lang(),o).format(t)}number(t,o){return t=Number(t),isNaN(t)?"":new Intl.NumberFormat(this.lang(),o).format(t)}relativeTime(t,o,r){return new Intl.RelativeTimeFormat(this.lang(),r).format(t,o)}};var go={$code:"en",$name:"English",$dir:"ltr",allTagsRemoved:"All tags removed",am:"AM",autosizeColumn:"Autosize column",captions:"Captions",carousel:"Carousel",chooseDate:"Choose date",chooseDecade:"Choose decade",chooseMonth:"Choose month",chooseTime:"Choose time",chooseYear:"Choose year",clearEntry:"Clear entry",clearFilter:"Clear filter",clearSort:"Clear sort",close:"Close",closeCalendar:"Close calendar",closeTimeInput:"Close time picker",collapseRow:"Collapse row",columnMenu:"Column options",columnMovedToPosition:(e,t,o)=>`${e} moved to position ${t} of ${o}`,columns:"Columns",compactPageXOfY:(e,t)=>`${e} of ${t}`,completed:"Completed",copied:"Copied",copy:"Copy",createOption:e=>`Create "${e}"`,currentlyPlaying:"currently playing",currentValue:"Current value",date:"Date",datePickerKeyboardHelp:"Use arrow keys to change values; press Alt+Down Arrow to open the calendar.",day:"Day",dayPeriod:"AM/PM",decrement:"Decrement",deselectAllRows:"Deselect all rows",disabled:"Disabled",dropFileHere:"Drop file here or click to browse",dropFilesHere:"Drop files here or click to browse",empty:"Empty",endDate:"End date",enterFullscreen:"Enter fullscreen",error:"Error",exitFullscreen:"Exit fullscreen",expandRow:"Expand row",filterByColumn:e=>`Filter by ${e}`,filterFrom:"From",filterMax:"Max",filterMin:"Min",filterTo:"To",firstPage:"First page",goToSlide:(e,t)=>`Go to slide ${e} of ${t}`,hideColumn:"Hide column",hidePassword:"Hide password",hour:"Hour",incompleteDate:"Enter a valid date.",increment:"Increment",jumpBackwardX:e=>`Jump back ${e} pages`,jumpForwardX:e=>`Jump forward ${e} pages`,lastPage:"Last page",loading:"Loading",locked:"Locked",minute:"Minute",month:"Month",moreOptions:"More Options",mute:"Mute",nextDecade:"Next decade",nextMonth:"Next month",nextPage:"Next page",nextSlide:"Next slide",nextVideo:"Next Video",nextYear:"Next year",noData:"No data",noOptions:"No options",noResults:"No matching results",notCompleted:"Not completed",now:"Now",numCharacters:e=>e===1?"1 character":`${e} characters`,numCharactersRemaining:e=>e===1?"1 character remaining":`${e} characters remaining`,numOptionsAvailable:e=>e===0?"No options available":e===1?"1 option available":`${e} options available`,numOptionsSelected:e=>e===0?"No options selected":e===1?"1 option selected":`${e} options selected`,numRowsCopied:e=>e===1?"1 row copied":`${e} rows copied`,numRowsSelected:e=>e===1?"1 row selected":`${e} rows selected`,optionPosition:(e,t,o)=>`${e}, ${t} of ${o}`,optionsLoadError:"Options could not be loaded",pageXOfY:(e,t)=>`Page ${e} of ${t}`,pagination:"Pagination",pause:"Pause",pauseAnimation:"Pause animation",pictureInPicture:"Picture in picture",pinLeft:"Pin left",pinRight:"Pin right",play:"Play",playAnimation:"Play animation",playbackSpeed:"Playback speed",playlist:"Playlist",pm:"PM",previousDecade:"Previous decade",previousMonth:"Previous month",previousPage:"Previous page",previousSlide:"Previous slide",previousVideo:"Previous video",previousYear:"Previous year",progress:"Progress",rangeTooLong:e=>e===1?"Select a range no longer than 1 day":`Select a range no longer than ${e} days`,rangeTooShort:e=>e===1?"Select a range at least 1 day long":`Select a range at least ${e} days long`,readonly:"Read-only",remove:"Remove",resetColumns:"Reset columns",resize:"Resize",resizeColumn:"Resize column",rowsPerPage:"Rows per page",scrollableRegion:"Scrollable region",scrollToEnd:"Scroll to end",scrollToStart:"Scroll to start",search:"Search",second:"Second",seek:"Seek",seekProgress:(e,t)=>`${e} of ${t}`,selectAColorFromTheScreen:"Select a color from the screen",selectAllRows:"Select all rows",selected:"Selected",selectedDateLabel:e=>`Selected: ${e}`,selectedRangeLabel:e=>`Selected range: ${e}`,selectGroup:"Select group",selectionCleared:"Selection cleared",selectRow:"Select row",showingNofMRows:(e,t)=>`Showing ${e} of ${t} rows`,showingXtoYofZ:(e,t,o)=>`${e}\u2013${t} of ${o}`,showPassword:"Show password",slideNum:e=>`Slide ${e}`,sortAscending:"Sort ascending",sortColumn:"Sort column",sortDescending:"Sort descending",startDate:"Start date",steps:"Steps",stepXOfY:(e,t)=>`Step ${e} of ${t}`,tagAdded:e=>`${e} added`,tagAlreadyAdded:e=>`${e} is already added`,tagInputKeyboardHelp:"Press Backspace or Delete to remove this tag.",tagRemoved:e=>`${e} removed`,time:"Time",timeInputKeyboardHelp:"Use arrow keys to change values; press Alt+Down Arrow to open the time picker.",today:"Today",toggleColorFormat:"Toggle color format",tooFewTags:e=>e===1?"Add at least 1 tag":`Add at least ${e} tags`,tooManyTags:e=>e===1?"Add no more than 1 tag":`Add no more than ${e} tags`,unmute:"Unmute",unpin:"Unpin",unpinColumn:"Unpin column",videoPlayer:"Video player",volume:"Volume",year:"Year",zoomIn:"Zoom in",zoomOut:"Zoom out"};zt(go);var wo=go;var te=class extends Qt{lang(){return this.host.didSSR&&!this.host.hasUpdated?this.host.lang||"en":super.lang()}};zt(wo);var F=Math.min,N=Math.max,Ht=Math.round,Ft=Math.floor,q=e=>({x:e,y:e}),Pr={left:"right",right:"left",bottom:"top",top:"bottom"};function Ee(e,t,o){return N(e,F(t,o))}function ut(e,t){return typeof e=="function"?e(t):e}function it(e){return e.split("-")[0]}function ft(e){return e.split("-")[1]}function Se(e){return e==="x"?"y":"x"}function oe(e){return e==="y"?"height":"width"}function W(e){let t=e[0];return t==="t"||t==="b"?"y":"x"}function re(e){return Se(W(e))}function bo(e,t,o){o===void 0&&(o=!1);let r=ft(e),i=re(e),n=oe(i),s=i==="x"?r===(o?"end":"start")?"right":"left":r==="start"?"bottom":"top";return t.reference[n]>t.floating[n]&&(s=Ut(s)),[s,Ut(s)]}function xo(e){let t=Ut(e);return[ee(e),t,ee(t)]}function ee(e){return e.includes("start")?e.replace("start","end"):e.replace("end","start")}var vo=["left","right"],yo=["right","left"],Or=["top","bottom"],Rr=["bottom","top"];function Tr(e,t,o){switch(e){case"top":case"bottom":return o?t?yo:vo:t?vo:yo;case"left":case"right":return t?Or:Rr;default:return[]}}function Ao(e,t,o,r){let i=ft(e),n=Tr(it(e),o==="start",r);return i&&(n=n.map(s=>s+"-"+i),t&&(n=n.concat(n.map(ee)))),n}function Ut(e){let t=it(e);return Pr[t]+e.slice(t.length)}function kr(e){var t,o,r,i;return{top:(t=e.top)!=null?t:0,right:(o=e.right)!=null?o:0,bottom:(r=e.bottom)!=null?r:0,left:(i=e.left)!=null?i:0}}function _e(e){return typeof e!="number"?kr(e):{top:e,right:e,bottom:e,left:e}}function mt(e){let{x:t,y:o,width:r,height:i}=e;return{width:r,height:i,top:o,left:t,right:t+r,bottom:o+i,x:t,y:o}}function $o(e,t,o){let{reference:r,floating:i}=e,n=W(t),s=re(t),l=oe(s),a=it(t),c=n==="y",h=r.x+r.width/2-i.width/2,d=r.y+r.height/2-i.height/2,u=r[l]/2-i[l]/2,p;switch(a){case"top":p={x:h,y:r.y-i.height};break;case"bottom":p={x:h,y:r.y+r.height};break;case"right":p={x:r.x+r.width,y:d};break;case"left":p={x:r.x-i.width,y:d};break;default:p={x:r.x,y:r.y}}let f=ft(t);return f&&(p[s]+=u*(f==="end"?1:-1)*(o&&c?-1:1)),p}async function Eo(e,t){var o;t===void 0&&(t={});let{x:r,y:i,platform:n,rects:s,elements:l,strategy:a}=e,{boundary:c="clippingAncestors",rootBoundary:h="viewport",elementContext:d="floating",altBoundary:u=!1,padding:p=0}=ut(t,e),f=_e(p),y=l[u?d==="floating"?"reference":"floating":d],v=mt(await n.getClippingRect({element:(o=await(n.isElement==null?void 0:n.isElement(y)))==null||o?y:y.contextElement||await(n.getDocumentElement==null?void 0:n.getDocumentElement(l.floating)),boundary:c,rootBoundary:h,strategy:a})),x=d==="floating"?{x:r,y:i,width:s.floating.width,height:s.floating.height}:s.reference,A=await(n.getOffsetParent==null?void 0:n.getOffsetParent(l.floating)),$=await(n.isElement==null?void 0:n.isElement(A))&&await(n.getScale==null?void 0:n.getScale(A))||{x:1,y:1},O=mt(n.convertOffsetParentRelativeRectToViewportRelativeRect?await n.convertOffsetParentRelativeRectToViewportRelativeRect({elements:l,rect:x,offsetParent:A,strategy:a}):x);return{top:(v.top-O.top+f.top)/$.y,bottom:(O.bottom-v.bottom+f.bottom)/$.y,left:(v.left-O.left+f.left)/$.x,right:(O.right-v.right+f.right)/$.x}}var Lr=50,So=async(e,t,o)=>{let{placement:r="bottom",strategy:i="absolute",middleware:n=[],platform:s}=o,l=s.detectOverflow?s:{...s,detectOverflow:Eo},a=await(s.isRTL==null?void 0:s.isRTL(t)),c=await s.getElementRects({reference:e,floating:t,strategy:i}),{x:h,y:d}=$o(c,r,a),u=r,p=0,f={};for(let w=0;w<n.length;w++){let y=n[w];if(!y)continue;let{name:v,fn:x}=y,{x:A,y:$,data:O,reset:S}=await x({x:h,y:d,initialPlacement:r,placement:u,strategy:i,middlewareData:f,rects:c,platform:l,elements:{reference:e,floating:t}});h=A??h,d=$??d,f[v]={...f[v],...O},S&&p<Lr&&(p++,typeof S=="object"&&(S.placement&&(u=S.placement),S.rects&&(c=S.rects===!0?await s.getElementRects({reference:e,floating:t,strategy:i}):S.rects),{x:h,y:d}=$o(c,u,a)),w=-1)}return{x:h,y:d,placement:u,strategy:i,middlewareData:f}},_o=e=>({name:"arrow",options:e,async fn(t){let{x:o,y:r,placement:i,rects:n,platform:s,elements:l,middlewareData:a}=t,{element:c,padding:h=0}=ut(e,t)||{};if(c==null)return{};let d=_e(h),u={x:o,y:r},p=re(i),f=oe(p),w=await s.getDimensions(c),y=p==="y",v=y?"top":"left",x=y?"bottom":"right",A=y?"clientHeight":"clientWidth",$=n.reference[f]+n.reference[p]-u[p]-n.floating[f],O=u[p]-n.reference[p],S=await(s.getOffsetParent==null?void 0:s.getOffsetParent(c)),R=S?S[A]:0;(!R||!await(s.isElement==null?void 0:s.isElement(S)))&&(R=l.floating[A]||n.floating[f]);let k=$/2-O/2,U=R/2-w[f]/2-1,C=F(d[v],U),_t=F(d[x],U),Ct=R-w[f]-_t,H=R/2-w[f]/2+k,L=Ee(C,H,Ct),st=!a.arrow&&ft(i)!=null&&H!==L&&n.reference[f]/2-(H<C?C:_t)-w[f]/2<0,I=st?H<C?H-C:H-Ct:0;return{[p]:u[p]+I,data:{[p]:L,centerOffset:H-L-I,...st&&{alignmentOffset:I}},reset:st}}});var Co=function(e){return e===void 0&&(e={}),{name:"flip",options:e,async fn(t){var o,r;let{placement:i,middlewareData:n,rects:s,initialPlacement:l,platform:a,elements:c}=t,{mainAxis:h=!0,crossAxis:d=!0,fallbackPlacements:u,fallbackStrategy:p="bestFit",fallbackAxisSideDirection:f="none",flipAlignment:w=!0,...y}=ut(e,t);if((o=n.arrow)!=null&&o.alignmentOffset)return{};let v=it(i),x=W(l),A=it(l)===l,$=await(a.isRTL==null?void 0:a.isRTL(c.floating)),O=u||(A||!w?[Ut(l)]:xo(l)),S=f!=="none";!u&&S&&O.push(...Ao(l,w,f,$));let R=[l,...O],k=await a.detectOverflow(t,y),U=[],C=((r=n.flip)==null?void 0:r.overflows)||[];if(h&&U.push(k[v]),d){let L=bo(i,s,$);U.push(k[L[0]],k[L[1]])}if(C=[...C,{placement:i,overflows:U}],!U.every(L=>L<=0)){var _t,Ct;let L=(((_t=n.flip)==null?void 0:_t.index)||0)+1,st=R[L];if(st&&(!(d==="alignment"?x!==W(st):!1)||C.every(D=>W(D.placement)===x?D.overflows[0]>0:!0)))return{data:{index:L,overflows:C},reset:{placement:st}};let I=(Ct=C.filter(at=>at.overflows[0]<=0).sort((at,D)=>at.overflows[1]-D.overflows[1])[0])==null?void 0:Ct.placement;if(!I)switch(p){case"bestFit":{var H;let at=(H=C.filter(D=>{if(S){let J=W(D.placement);return J===x||J==="y"}return!0}).map(D=>[D.placement,D.overflows.filter(J=>J>0).reduce((J,sr)=>J+sr,0)]).sort((D,J)=>D[1]-J[1])[0])==null?void 0:H[0];at&&(I=at);break}case"initialPlacement":I=l;break}if(i!==I)return{reset:{placement:I}}}return{}}}};var Dr=new Set(["left","top"]);async function Mr(e,t){let{placement:o,platform:r,elements:i}=e,n=await(r.isRTL==null?void 0:r.isRTL(i.floating)),s=it(o),l=ft(o),a=W(o)==="y",c=Dr.has(s)?-1:1,h=n&&a?-1:1,d=ut(t,e),{mainAxis:u,crossAxis:p,alignmentAxis:f}=typeof d=="number"?{mainAxis:d,crossAxis:0,alignmentAxis:null}:{mainAxis:d.mainAxis||0,crossAxis:d.crossAxis||0,alignmentAxis:d.alignmentAxis};return l&&typeof f=="number"&&(p=l==="end"?f*-1:f),a?{x:p*h,y:u*c}:{x:u*c,y:p*h}}var Po=function(e){return e===void 0&&(e=0),{name:"offset",options:e,async fn(t){var o,r;let{x:i,y:n,placement:s,middlewareData:l}=t,a=await Mr(t,e);return s===((o=l.offset)==null?void 0:o.placement)&&(r=l.arrow)!=null&&r.alignmentOffset?{}:{x:i+a.x,y:n+a.y,data:{...a,placement:s}}}}},Oo=function(e){return e===void 0&&(e={}),{name:"shift",options:e,async fn(t){let{x:o,y:r,placement:i,platform:n}=t,{mainAxis:s=!0,crossAxis:l=!1,limiter:a={fn:x=>{let{x:A,y:$}=x;return{x:A,y:$}}},...c}=ut(e,t),h={x:o,y:r},d=await n.detectOverflow(t,c),u=W(i),p=Se(u),f=h[p],w=h[u],y=(x,A)=>Ee(A+d[x==="y"?"top":"left"],A,A-d[x==="y"?"bottom":"right"]);s&&(f=y(p,f)),l&&(w=y(u,w));let v=a.fn({...t,[p]:f,[u]:w});return{...v,data:{x:v.x-o,y:v.y-r,enabled:{[p]:s,[u]:l}}}}}};var Ro=function(e){return e===void 0&&(e={}),{name:"size",options:e,async fn(t){let{placement:o,rects:r,platform:i,elements:n}=t,{apply:s=()=>{},...l}=ut(e,t),a=await i.detectOverflow(t,l),c=it(o),h=ft(o),d=W(o)==="y",{width:u,height:p}=r.floating,f,w;c==="top"||c==="bottom"?(f=c,w=h===(await(i.isRTL==null?void 0:i.isRTL(n.floating))?"start":"end")?"left":"right"):(w=c,f=h==="end"?"top":"bottom");let y=p-a.top-a.bottom,v=u-a.left-a.right,x=F(p-a[f],y),A=F(u-a[w],v),$=t.middlewareData.shift,O=!$,S=x,R=A;$!=null&&$.enabled.x&&(R=v),$!=null&&$.enabled.y&&(S=y),O&&!h&&(d?R=u-2*N(a.left,a.right):S=p-2*N(a.top,a.bottom)),await s({...t,availableWidth:R,availableHeight:S});let k=await i.getDimensions(n.floating);return u!==k.width||p!==k.height?{reset:{rects:!0}}:{}}}};function ie(){return typeof window<"u"}function wt(e){return ko(e)?(e.nodeName||"").toLowerCase():"#document"}function P(e){var t;return(e==null||(t=e.ownerDocument)==null?void 0:t.defaultView)||window}function V(e){var t;return(t=(ko(e)?e.ownerDocument:e.document)||window.document)==null?void 0:t.documentElement}function ko(e){return ie()?e instanceof Node||e instanceof P(e).Node:!1}function B(e){return ie()?e instanceof Element||e instanceof P(e).Element:!1}function Z(e){return ie()?e instanceof HTMLElement||e instanceof P(e).HTMLElement:!1}function To(e){return!ie()||typeof ShadowRoot>"u"?!1:e instanceof ShadowRoot||e instanceof P(e).ShadowRoot}function qt(e){let{overflow:t,overflowX:o,overflowY:r,display:i}=z(e);return/auto|scroll|overlay|hidden|clip/.test(t+r+o)&&i!=="inline"&&i!=="contents"}function Lo(e){return/^(table|td|th)$/.test(wt(e))}function Wt(e){try{if(e.matches(":popover-open"))return!0}catch{}try{return e.matches(":modal")}catch{return!1}}var Nr=/transform|translate|scale|rotate|perspective|filter/,Br=/paint|layout|strict|content/,gt=e=>!!e&&e!=="none",Ce;function $t(e){let t=B(e)?z(e):e;return gt(t.transform)||gt(t.translate)||gt(t.scale)||gt(t.rotate)||gt(t.perspective)||!ne()&&(gt(t.backdropFilter)||gt(t.filter))||Nr.test(t.willChange||"")||Br.test(t.contain||"")}function Do(e){let t=nt(e);for(;Z(t)&&!Et(t);){if($t(t))return t;if(Wt(t))return null;t=nt(t)}return null}function ne(){return Ce==null&&(Ce=typeof CSS<"u"&&CSS.supports&&CSS.supports("-webkit-backdrop-filter","none")),Ce}function Et(e){return/^(html|body|#document)$/.test(wt(e))}function z(e){return P(e).getComputedStyle(e)}function Vt(e){return B(e)?{scrollLeft:e.scrollLeft,scrollTop:e.scrollTop}:{scrollLeft:e.scrollX,scrollTop:e.scrollY}}function nt(e){if(wt(e)==="html")return e;let t=e.assignedSlot||e.parentNode||To(e)&&e.host||V(e);return To(t)?t.host:t}function Mo(e){let t=nt(e);return Et(t)?(e.ownerDocument||e).body:Z(t)&&qt(t)?t:Mo(t)}function G(e,t,o){var r;t===void 0&&(t=[]),o===void 0&&(o=!0);let i=Mo(e),n=i===((r=e.ownerDocument)==null?void 0:r.body),s=P(i);if(n){let l=se(s);return t.concat(s,s.visualViewport||[],qt(i)?i:[],l&&o?G(l):[])}else return t.concat(i,G(i,[],o))}function se(e){return e.parent&&Object.getPrototypeOf(e.parent)?e.frameElement:null}function zo(e){let t=z(e),o=parseFloat(t.width)||0,r=parseFloat(t.height)||0,i=Z(e),n=i?e.offsetWidth:o,s=i?e.offsetHeight:r,l=Ht(o)!==n||Ht(r)!==s;return l&&(o=n,r=s),{width:o,height:r,$:l}}function Oe(e){return B(e)?e:e.contextElement}function St(e){let t=Oe(e);if(!Z(t))return q(1);let o=t.getBoundingClientRect(),{width:r,height:i,$:n}=zo(t),s=(n?Ht(o.width):o.width)/r,l=(n?Ht(o.height):o.height)/i;return(!s||!Number.isFinite(s))&&(s=1),(!l||!Number.isFinite(l))&&(l=1),{x:s,y:l}}var zr=q(0);function Uo(e){let t=P(e);return!ne()||!t.visualViewport?zr:{x:t.visualViewport.offsetLeft,y:t.visualViewport.offsetTop}}function Ur(e,t,o){return t===void 0&&(t=!1),!!o&&t&&o===P(e)}function vt(e,t,o,r){t===void 0&&(t=!1),o===void 0&&(o=!1);let i=e.getBoundingClientRect(),n=Oe(e),s=q(1);t&&(r?B(r)&&(s=St(r)):s=St(e));let l=Ur(n,o,r)?Uo(n):q(0),a=(i.left+l.x)/s.x,c=(i.top+l.y)/s.y,h=i.width/s.x,d=i.height/s.y;if(n&&r){let u=P(n),p=B(r)?P(r):r,f=u,w=se(f);for(;w&&p!==f;){let y=St(w),v=w.getBoundingClientRect(),x=z(w),A=v.left+(w.clientLeft+parseFloat(x.paddingLeft))*y.x,$=v.top+(w.clientTop+parseFloat(x.paddingTop))*y.y;a*=y.x,c*=y.y,h*=y.x,d*=y.y,a+=A,c+=$,f=P(w),w=se(f)}}return mt({width:h,height:d,x:a,y:c})}function ae(e,t){let o=Vt(e).scrollLeft;return t?t.left+o:vt(V(e)).left+o}function Ho(e,t){let o=e.getBoundingClientRect(),r=o.left+t.scrollLeft-ae(e,o),i=o.top+t.scrollTop;return{x:r,y:i}}function Hr(e){let{elements:t,rect:o,offsetParent:r,strategy:i}=e,n=i==="fixed",s=V(r),l=t?Wt(t.floating):!1;if(r===s||l&&n)return o;let a={scrollLeft:0,scrollTop:0},c=q(1),h=q(0),d=Z(r);if((d||!n)&&((wt(r)!=="body"||qt(s))&&(a=Vt(r)),d)){let p=vt(r);c=St(r),h.x=p.x+r.clientLeft,h.y=p.y+r.clientTop}let u=s&&!d&&!n?Ho(s,a):q(0);return{width:o.width*c.x,height:o.height*c.y,x:o.x*c.x-a.scrollLeft*c.x+h.x+u.x,y:o.y*c.y-a.scrollTop*c.y+h.y+u.y}}function Fr(e){return e.getClientRects?Array.from(e.getClientRects()):[]}function qr(e){let t=Vt(e),o=e.ownerDocument.body,r=N(e.scrollWidth,e.clientWidth,o.scrollWidth,o.clientWidth),i=N(e.scrollHeight,e.clientHeight,o.scrollHeight,o.clientHeight),n=-t.scrollLeft+ae(e),s=-t.scrollTop;return z(o).direction==="rtl"&&(n+=N(e.clientWidth,o.clientWidth)-r),{width:r,height:i,x:n,y:s}}var Wr=25;function Vr(e,t,o){o===void 0&&(o="viewport");let r=o==="layoutViewport",i=P(e),n=V(e),s=i.visualViewport,l=n.clientWidth,a=n.clientHeight,c=0,h=0;if(s){let u=!ne()||t==="fixed";r?u||(c=-s.offsetLeft,h=-s.offsetTop):(l=s.width,a=s.height,u&&(c=s.offsetLeft,h=s.offsetTop))}if(ae(n)<=0){let u=n.ownerDocument,p=u.body,f=getComputedStyle(p),w=u.compatMode==="CSS1Compat"&&parseFloat(f.marginLeft)+parseFloat(f.marginRight)||0,y=Math.abs(n.clientWidth-p.clientWidth-w),v=getComputedStyle(n).scrollbarGutter==="stable both-edges"?y/2:y;v<=Wr&&(l-=v)}return{width:l,height:a,x:c,y:h}}function Ir(e,t){let o=vt(e,!0,t==="fixed"),r=o.top+e.clientTop,i=o.left+e.clientLeft,n=St(e),s=e.clientWidth*n.x,l=e.clientHeight*n.y,a=i*n.x,c=r*n.y;return{width:s,height:l,x:a,y:c}}function No(e,t,o){let r;if(t==="viewport"||t==="layoutViewport")r=Vr(e,o,t);else if(t==="document")r=qr(V(e));else if(B(t))r=Ir(t,o);else{let i=Uo(e);r={x:t.x-i.x,y:t.y-i.y,width:t.width,height:t.height}}return mt(r)}function jr(e,t){let o=t.get(e);if(o)return o;let r=G(e,[],!1).filter(l=>B(l)&&wt(l)!=="body"),i=null,n=z(e).position==="fixed",s=n?nt(e):e;for(;B(s)&&!Et(s);){let l=z(s),a=$t(s),c=i?i.position:n?"fixed":"";!a&&(c==="fixed"||c==="absolute"&&l.position==="static")?r=r.filter(d=>d!==s):i=l,s=nt(s)}return t.set(e,r),r}function Yr(e){let{element:t,boundary:o,rootBoundary:r,strategy:i}=e,s=[...o==="clippingAncestors"?Wt(t)?[]:jr(t,this._c):[].concat(o),r],l=No(t,s[0],i),a=l.top,c=l.right,h=l.bottom,d=l.left;for(let u=1;u<s.length;u++){let p=No(t,s[u],i);a=N(p.top,a),c=F(p.right,c),h=F(p.bottom,h),d=N(p.left,d)}return{width:c-d,height:h-a,x:d,y:a}}function Xr(e){let{width:t,height:o}=zo(e);return{width:t,height:o}}function Kr(e,t,o){let r=Z(t),i=V(t),n=o==="fixed",s=vt(e,!0,n,t),l={scrollLeft:0,scrollTop:0},a=q(0);if((r||!n)&&((wt(t)!=="body"||qt(i))&&(l=Vt(t)),r)){let u=vt(t,!0,n,t);a.x=u.x+t.clientLeft,a.y=u.y+t.clientTop}!r&&i&&(a.x=ae(i));let c=i&&!r&&!n?Ho(i,l):q(0),h=s.left+l.scrollLeft-a.x-c.x,d=s.top+l.scrollTop-a.y-c.y;return{x:h,y:d,width:s.width,height:s.height}}function Pe(e){return z(e).position==="static"}function Bo(e,t){if(!Z(e)||z(e).position==="fixed")return null;if(t)return t(e);let o=e.offsetParent;return V(e)===o&&(o=o.ownerDocument.body),o}function Fo(e,t){let o=P(e);if(Wt(e))return o;if(!Z(e)){let i=nt(e);for(;i&&!Et(i);){if(B(i)&&!Pe(i))return i;i=nt(i)}return o}let r=Bo(e,t);for(;r&&Lo(r)&&Pe(r);)r=Bo(r,t);return r&&Et(r)&&Pe(r)&&!$t(r)?o:r||Do(e)||o}var Gr=async function(e){let t=this.getOffsetParent||Fo,o=this.getDimensions,r=await o(e.floating);return{reference:Kr(e.reference,await t(e.floating),e.strategy),floating:{x:0,y:0,width:r.width,height:r.height}}};function Zr(e){return z(e).direction==="rtl"}var It={convertOffsetParentRelativeRectToViewportRelativeRect:Hr,getDocumentElement:V,getClippingRect:Yr,getOffsetParent:Fo,getElementRects:Gr,getClientRects:Fr,getDimensions:Xr,getScale:St,isElement:B,isRTL:Zr};function qo(e,t){return e.x===t.x&&e.y===t.y&&e.width===t.width&&e.height===t.height}function Jr(e,t,o){let r=null,i,n=V(e);function s(){var h;clearTimeout(i),(h=r)==null||h.disconnect(),r=null}function l(h,d){h===void 0&&(h=!1),d===void 0&&(d=1),s();let u=e.getBoundingClientRect(),{left:p,top:f,width:w,height:y}=u;if(h||t(),!w||!y)return;let v=Ft(f),x=Ft(n.clientWidth-(p+w)),A=Ft(n.clientHeight-(f+y)),$=Ft(p),S={rootMargin:-v+"px "+-x+"px "+-A+"px "+-$+"px",threshold:N(0,F(1,d))||1},R=!0;function k(U){let C=U[0].intersectionRatio;if(!qo(u,e.getBoundingClientRect()))return l();if(C!==d){if(!R)return l();C?l(!1,C):i=setTimeout(()=>{l(!1,1e-7)},1e3)}R=!1}try{r=new IntersectionObserver(k,{...S,root:n.ownerDocument})}catch{r=new IntersectionObserver(k,S)}r.observe(e)}let a=P(e),c=()=>l(o);return a.addEventListener("resize",c),l(!0),()=>{a.removeEventListener("resize",c),s()}}function Wo(e,t,o,r){r===void 0&&(r={});let{ancestorScroll:i=!0,ancestorResize:n=!0,elementResize:s=typeof ResizeObserver=="function",layoutShift:l=typeof IntersectionObserver=="function",animationFrame:a=!1}=r,c=Oe(e),h=i||n?[...c?G(c):[],...t?G(t):[]]:[];h.forEach(v=>{i&&v.addEventListener("scroll",o),n&&v.addEventListener("resize",o)});let d=c&&l?Jr(c,o,n):null,u=-1,p=null;s&&(p=new ResizeObserver(v=>{let[x]=v;x&&x.target===c&&p&&t&&(p.unobserve(t),cancelAnimationFrame(u),u=requestAnimationFrame(()=>{var A;(A=p)==null||A.observe(t)})),o()}),c&&!a&&p.observe(c),t&&p.observe(t));let f,w=a?vt(e):null;a&&y();function y(){let v=vt(e);w&&!qo(w,v)&&o(),w=v,f=requestAnimationFrame(y)}return o(),()=>{var v;h.forEach(x=>{i&&x.removeEventListener("scroll",o),n&&x.removeEventListener("resize",o)}),d?.(),(v=p)==null||v.disconnect(),p=null,a&&cancelAnimationFrame(f)}}var Vo=Po;var Io=Oo,jo=Co,Re=Ro;var Yo=_o;var Xo=(e,t,o)=>{let r=new Map,i=o??{},n={...It,...i.platform,_c:r};return So(e,t,{...i,platform:n})};function Ko(e){return Qr(e)}function Te(e){return e.assignedSlot?e.assignedSlot:e.parentNode instanceof ShadowRoot?e.parentNode.host:e.parentNode}function Qr(e){for(let t=e;t;t=Te(t))if(t instanceof Element&&getComputedStyle(t).display==="none")return null;for(let t=Te(e);t;t=Te(t)){if(!(t instanceof Element))continue;let o=getComputedStyle(t);if(o.display!=="contents"&&(o.position!=="static"||$t(o)||t.tagName==="BODY"))return t}return null}var Go={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Zo=e=>(...t)=>({_$litDirective$:e,values:t}),le=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,o,r){this._$Ct=t,this._$AM=o,this._$Ci=r}_$AS(t,o){return this.update(t,o)}update(t,o){return this.render(...o)}};var jt=Zo(class extends le{constructor(e){if(super(e),e.type!==Go.ATTRIBUTE||e.name!=="class"||e.strings?.length>2)throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.")}render(e){return" "+Object.keys(e).filter(t=>e[t]).join(" ")+" "}update(e,[t]){if(this.st===void 0){this.st=new Set,e.strings!==void 0&&(this.nt=new Set(e.strings.join(" ").split(/\s/).filter(r=>r!=="")));for(let r in t)t[r]&&!this.nt?.has(r)&&this.st.add(r);return this.render(t)}let o=e.element.classList;for(let r of this.st)r in t||(o.remove(r),this.st.delete(r));for(let r in t){let i=!!t[r];i===this.st.has(r)||this.nt?.has(r)||(i?(o.add(r),this.st.add(r)):(o.remove(r),this.st.delete(r)))}return Y}});function Jo(e){return e!==null&&typeof e=="object"&&"getBoundingClientRect"in e&&("contextElement"in e?e instanceof Element:!0)}var ti=!!globalThis?.HTMLElement?.prototype.hasOwnProperty("popover"),b=class extends M{constructor(){super(...arguments),this.localize=new te(this),this.SUPPORTS_POPOVER=!1,this.active=!1,this.placement="top",this.boundary="viewport",this.distance=0,this.skidding=0,this.arrow=!1,this.arrowPlacement="anchor",this.arrowPadding=10,this.flip=!1,this.flipFallbackPlacements="",this.flipFallbackStrategy="best-fit",this.flipPadding=0,this.shift=!1,this.shiftPadding=0,this.autoSizePadding=0,this.hoverBridge=!1,this.updateHoverBridge=()=>{if(this.hoverBridge&&this.anchorEl&&this.popup){let e=this.anchorEl.getBoundingClientRect(),t=this.popup.getBoundingClientRect(),o=this.placement.includes("top")||this.placement.includes("bottom"),r=0,i=0,n=0,s=0,l=0,a=0,c=0,h=0;o?e.top<t.top?(r=e.left,i=e.bottom,n=e.right,s=e.bottom,l=t.left,a=t.top,c=t.right,h=t.top):(r=t.left,i=t.bottom,n=t.right,s=t.bottom,l=e.left,a=e.top,c=e.right,h=e.top):e.left<t.left?(r=e.right,i=e.top,n=t.left,s=t.top,l=e.right,a=e.bottom,c=t.left,h=t.bottom):(r=t.right,i=t.top,n=e.left,s=e.top,l=t.right,a=t.bottom,c=e.left,h=e.bottom),this.style.setProperty("--hover-bridge-top-left-x",`${r}px`),this.style.setProperty("--hover-bridge-top-left-y",`${i}px`),this.style.setProperty("--hover-bridge-top-right-x",`${n}px`),this.style.setProperty("--hover-bridge-top-right-y",`${s}px`),this.style.setProperty("--hover-bridge-bottom-left-x",`${l}px`),this.style.setProperty("--hover-bridge-bottom-left-y",`${a}px`),this.style.setProperty("--hover-bridge-bottom-right-x",`${c}px`),this.style.setProperty("--hover-bridge-bottom-right-y",`${h}px`)}}}async connectedCallback(){super.connectedCallback(),await this.updateComplete,this.SUPPORTS_POPOVER=ti,this.start()}disconnectedCallback(){super.disconnectedCallback(),this.stop()}async updated(e){super.updated(e),e.has("active")&&(this.active?this.start():this.stop()),e.has("anchor")&&this.handleAnchorChange(),this.active&&(await this.updateComplete,this.reposition())}async handleAnchorChange(){if(await this.stop(),this.anchor&&typeof this.anchor=="string"){let e=this.getRootNode();this.anchorEl=e.getElementById(this.anchor)}else this.anchor instanceof Element||Jo(this.anchor)?this.anchorEl=this.anchor:this.anchorEl=this.querySelector('[slot="anchor"]');this.anchorEl instanceof HTMLSlotElement&&(this.anchorEl=this.anchorEl.assignedElements({flatten:!0})[0]),this.anchorEl&&this.start()}start(){!this.anchorEl||!this.active||!this.isConnected||(this.popup?.showPopover?.(),this.cleanup=Wo(this.anchorEl,this.popup,()=>{this.reposition()}))}async stop(){return new Promise(e=>{this.popup?.hidePopover?.(),this.cleanup?(this.cleanup(),this.cleanup=void 0,this.removeAttribute("data-current-placement"),this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height"),requestAnimationFrame(()=>e())):e()})}reposition(){if(!this.active||!this.anchorEl||!this.popup)return;let e=[Vo({mainAxis:this.distance,crossAxis:this.skidding})];this.sync?e.push(Re({apply:({rects:r})=>{let i=this.sync==="width"||this.sync==="both",n=this.sync==="height"||this.sync==="both";this.popup.style.width=i?`${r.reference.width}px`:"",this.popup.style.height=n?`${r.reference.height}px`:""}})):(this.popup.style.width="",this.popup.style.height="");let t;this.SUPPORTS_POPOVER&&!Jo(this.anchor)&&this.boundary==="scroll"&&(t=G(this.anchorEl).filter(r=>r instanceof Element)),this.flip&&e.push(jo({boundary:this.flipBoundary||t,fallbackPlacements:this.flipFallbackPlacements,fallbackStrategy:this.flipFallbackStrategy==="best-fit"?"bestFit":"initialPlacement",padding:this.flipPadding})),this.shift&&e.push(Io({boundary:this.shiftBoundary||t,padding:this.shiftPadding})),this.autoSize?e.push(Re({boundary:this.autoSizeBoundary||t,padding:this.autoSizePadding,apply:({availableWidth:r,availableHeight:i})=>{this.autoSize==="vertical"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-height",`${i}px`):this.style.removeProperty("--auto-size-available-height"),this.autoSize==="horizontal"||this.autoSize==="both"?this.style.setProperty("--auto-size-available-width",`${r}px`):this.style.removeProperty("--auto-size-available-width")}})):(this.style.removeProperty("--auto-size-available-width"),this.style.removeProperty("--auto-size-available-height")),this.arrow&&e.push(Yo({element:this.arrowEl,padding:this.arrowPadding}));let o=this.SUPPORTS_POPOVER?r=>It.getOffsetParent(r,Ko):It.getOffsetParent;Xo(this.anchorEl,this.popup,{placement:this.placement,middleware:e,strategy:this.SUPPORTS_POPOVER?"absolute":"fixed",platform:{...It,getOffsetParent:o}}).then(({x:r,y:i,middlewareData:n,placement:s})=>{let l=this.localize.dir()==="rtl",a={top:"bottom",right:"left",bottom:"top",left:"right"}[s.split("-")[0]];if(this.setAttribute("data-current-placement",s),Object.assign(this.popup.style,{left:`${r}px`,top:`${i}px`}),this.arrow){let c=n.arrow.x,h=n.arrow.y,d="",u="",p="",f="";if(this.arrowPlacement==="start"){let w=typeof c=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";d=typeof h=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"",u=l?w:"",f=l?"":w}else if(this.arrowPlacement==="end"){let w=typeof c=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:"";u=l?"":w,f=l?w:"",p=typeof h=="number"?`calc(${this.arrowPadding}px - var(--arrow-padding-offset))`:""}else this.arrowPlacement==="center"?(f=typeof c=="number"?"calc(50% - var(--arrow-size-diagonal))":"",d=typeof h=="number"?"calc(50% - var(--arrow-size-diagonal))":""):(f=typeof c=="number"?`${c}px`:"",d=typeof h=="number"?`${h}px`:"");Object.assign(this.arrowEl.style,{top:d,right:u,bottom:p,left:f,[a]:"calc(var(--arrow-base-offset) - var(--arrow-size-diagonal))"})}}),requestAnimationFrame(()=>this.updateHoverBridge()),this.dispatchEvent(new po)}render(){return X`
      <slot name="anchor" @slotchange=${this.handleAnchorChange}></slot>

      <span
        part="hover-bridge"
        class=${jt({"popup-hover-bridge":!0,"popup-hover-bridge-visible":this.hoverBridge&&this.active})}
      ></span>

      <div
        popover="manual"
        part="popup"
        class=${jt({popup:!0,"popup-active":this.active,"popup-fixed":!this.SUPPORTS_POPOVER,"popup-has-arrow":this.arrow})}
      >
        <slot></slot>
        ${this.arrow?X`<div part="arrow" class="arrow" role="presentation"></div>`:""}
      </div>
    `}};b.css=uo;m([pt(".popup")],b.prototype,"popup",2);m([pt(".arrow")],b.prototype,"arrowEl",2);m([g({attribute:!1,type:Boolean})],b.prototype,"SUPPORTS_POPOVER",2);m([g()],b.prototype,"anchor",2);m([g({type:Boolean,reflect:!0})],b.prototype,"active",2);m([g({reflect:!0})],b.prototype,"placement",2);m([g()],b.prototype,"boundary",2);m([g({type:Number})],b.prototype,"distance",2);m([g({type:Number})],b.prototype,"skidding",2);m([g({type:Boolean})],b.prototype,"arrow",2);m([g({attribute:"arrow-placement"})],b.prototype,"arrowPlacement",2);m([g({attribute:"arrow-padding",type:Number})],b.prototype,"arrowPadding",2);m([g({type:Boolean})],b.prototype,"flip",2);m([g({attribute:"flip-fallback-placements",converter:{fromAttribute:e=>e.split(" ").map(t=>t.trim()).filter(t=>t!==""),toAttribute:e=>e.join(" ")}})],b.prototype,"flipFallbackPlacements",2);m([g({attribute:"flip-fallback-strategy"})],b.prototype,"flipFallbackStrategy",2);m([g({type:Object})],b.prototype,"flipBoundary",2);m([g({attribute:"flip-padding",type:Number})],b.prototype,"flipPadding",2);m([g({type:Boolean})],b.prototype,"shift",2);m([g({type:Object})],b.prototype,"shiftBoundary",2);m([g({attribute:"shift-padding",type:Number})],b.prototype,"shiftPadding",2);m([g({attribute:"auto-size"})],b.prototype,"autoSize",2);m([g()],b.prototype,"sync",2);m([g({type:Object})],b.prototype,"autoSizeBoundary",2);m([g({attribute:"auto-size-padding",type:Number})],b.prototype,"autoSizePadding",2);m([g({attribute:"hover-bridge",type:Boolean})],b.prototype,"hoverBridge",2);b=m([ot("wa-popup")],b);var yt=[];function Qo(e){ce(e),yt.push(e)}function ce(e){for(let t=yt.length-1;t>=0;t--)if(yt[t]===e){yt.splice(t,1);break}}function tr(e){return yt.length>0&&yt[yt.length-1]===e}var er="useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict";var or=(e=21)=>{let t="",o=crypto.getRandomValues(new Uint8Array(e|=0));for(;e--;)t+=er[o[e]&63];return t};function rr(e=""){return`${e}${or()}`}function ke(e,t){return new Promise(o=>{function r(i){i.target===e&&(e.removeEventListener(t,r),o())}e.addEventListener(t,r)})}function Le(e,t){return new Promise(o=>{let r=new AbortController,{signal:i}=r;if(e.classList.contains(t))return;e.classList.add(t);let n=!1,s=()=>{n||(n=!0,e.classList.remove(t),o(),r.abort())};e.addEventListener("animationend",s,{once:!0,signal:i}),e.addEventListener("animationcancel",s,{once:!0,signal:i}),requestAnimationFrame(()=>{!n&&e.getAnimations().length===0&&s()})})}function Yt(e,t){let o={waitUntilFirstUpdate:!1,...t};return(r,i)=>{let{update:n}=r,s=Array.isArray(e)?e:[e];r.update=function(l){s.forEach(a=>{let c=a;if(l.has(c)){let h=l.get(c),d=this[c];h!==d&&(!o.waitUntilFirstUpdate||this.hasUpdated)&&this[i](h,d)}}),n.call(this,l)}}}function ir(e,t){for(;t;){if(t===e)return!0;t instanceof Element&&t.assignedSlot?t=t.assignedSlot:t.parentNode?t=t.parentNode:t instanceof ShadowRoot?t=t.host:t=null}return!1}var E=class extends M{constructor(){super(...arguments),this.dismissedByPress=!1,this.placement="top",this.disabled=!1,this.distance=8,this.open=!1,this.skidding=0,this.showDelay=150,this.hideDelay=0,this.trigger="hover focus",this.withoutArrow=!1,this.for=null,this.anchor=null,this.eventController=new AbortController,this.handleBlur=()=>{this.dismissedByPress=!1,this.hasTrigger("focus")&&this.hide()},this.handleClick=()=>{if(this.hasTrigger("click")){this.open?this.hide():this.show();return}this.hasTrigger("manual")||this.lightDismiss()},this.handleFocus=()=>{this.dismissedByPress||this.hasTrigger("focus")&&this.show()},this.handleMouseDown=()=>{this.hasTrigger("click")||this.hasTrigger("manual")||this.lightDismiss()},this.handleDocumentKeyDown=e=>{this.hasTrigger("manual")||e.key==="Escape"&&this.open&&tr(this)&&(e.preventDefault(),e.stopPropagation(),this.hide())},this.handleDocumentClick=e=>{this.hasTrigger("manual")||this.anchor&&e.composedPath().includes(this.anchor)||this.hide()},this.handleMouseOver=()=>{this.dismissedByPress||this.hasTrigger("hover")&&(clearTimeout(this.hoverTimeout),this.hoverTimeout=window.setTimeout(()=>this.show(),this.showDelay))},this.handleMouseOut=e=>{let t=e.relatedTarget,o=!!(t&&this.anchor&&ir(this.anchor,t)),r=!!(t&&ir(this,t));o||r||(this.dismissedByPress=!1,this.hasTrigger("hover")&&(clearTimeout(this.hoverTimeout),this.hoverTimeout=window.setTimeout(()=>{this.hide()},this.hideDelay)))}}connectedCallback(){super.connectedCallback(),typeof document<"u"&&(this.eventController.signal.aborted&&(this.eventController=new AbortController),this.addEventListener("mouseout",this.handleMouseOut),this.dismissedByPress=!1,this.open&&(this.open=!1,this.updateComplete.then(()=>{this.open=!0})),this.id||(this.id=rr("wa-tooltip-")),this.for&&this.anchor?(this.anchor=null,this.handleForChange()):this.for&&this.handleForChange())}disconnectedCallback(){super.disconnectedCallback(),document.removeEventListener("keydown",this.handleDocumentKeyDown),document.removeEventListener("click",this.handleDocumentClick),ce(this),this.eventController.abort(),this.anchor&&this.removeFromAriaLabelledBy(this.anchor,this.id)}firstUpdated(e){this.body.hidden=!this.open,this.open&&(this.popup.active=!0,this.popup.reposition()),super.firstUpdated(e)}lightDismiss(){clearTimeout(this.hoverTimeout),this.dismissedByPress=!0,this.hide()}hasTrigger(e){return this.trigger.split(" ").includes(e)}addToAriaLabelledBy(e,t){let r=(e.getAttribute("aria-labelledby")||"").split(/\s+/).filter(Boolean);r.includes(t)||(r.push(t),e.setAttribute("aria-labelledby",r.join(" ")))}removeFromAriaLabelledBy(e,t){let i=(e.getAttribute("aria-labelledby")||"").split(/\s+/).filter(Boolean).filter(n=>n!==t);i.length>0?e.setAttribute("aria-labelledby",i.join(" ")):e.removeAttribute("aria-labelledby")}async handleOpenChange(){if(this.open){if(this.disabled)return;let e=new ao;if(this.dispatchEvent(e),e.defaultPrevented){this.open=!1;return}this.hasTrigger("manual")||(document.addEventListener("keydown",this.handleDocumentKeyDown,{signal:this.eventController.signal}),document.addEventListener("click",this.handleDocumentClick,{signal:this.eventController.signal}),Qo(this)),this.body.hidden=!1,this.popup.active=!0,await Le(this.popup.popup,"show-with-scale"),this.popup.reposition(),this.dispatchEvent(new ho)}else{let e=new lo;if(this.dispatchEvent(e),e.defaultPrevented){this.open=!0;return}document.removeEventListener("keydown",this.handleDocumentKeyDown),document.removeEventListener("click",this.handleDocumentClick),ce(this),await Le(this.popup.popup,"hide-with-scale"),this.popup.active=!1,this.body.hidden=!0,this.dispatchEvent(new co)}}handleForChange(){let e=this.getRootNode?.();if(!e)return;let t=this.for?e.getElementById?.(this.for):null,o=this.anchor;if(t===o)return;this.dismissedByPress=!1;let{signal:r}=this.eventController;t&&(this.addToAriaLabelledBy(t,this.id),t.addEventListener("blur",this.handleBlur,{capture:!0,signal:r}),t.addEventListener("focus",this.handleFocus,{capture:!0,signal:r}),t.addEventListener("click",this.handleClick,{signal:r}),t.addEventListener("mousedown",this.handleMouseDown,{signal:r}),t.addEventListener("mouseover",this.handleMouseOver,{signal:r}),t.addEventListener("mouseout",this.handleMouseOut,{signal:r})),o&&(this.removeFromAriaLabelledBy(o,this.id),o.removeEventListener("blur",this.handleBlur,{capture:!0}),o.removeEventListener("focus",this.handleFocus,{capture:!0}),o.removeEventListener("click",this.handleClick),o.removeEventListener("mousedown",this.handleMouseDown),o.removeEventListener("mouseover",this.handleMouseOver),o.removeEventListener("mouseout",this.handleMouseOut)),this.anchor=t}async handleOptionsChange(){this.hasUpdated&&(await this.updateComplete,this.popup.reposition())}handleDisabledChange(){this.disabled&&this.open&&this.hide()}async show(){if(!this.open)return this.open=!0,ke(this,"wa-after-show")}async hide(){if(this.open)return this.open=!1,ke(this,"wa-after-hide")}render(){return X`
      <wa-popup
        part="base tooltip"
        exportparts="
          popup:base__popup,
          arrow:base__arrow
        "
        class=${jt({tooltip:!0,"tooltip-open":this.open})}
        placement=${this.placement}
        distance=${this.distance}
        skidding=${this.skidding}
        flip
        shift
        ?arrow=${!this.withoutArrow}
        hover-bridge
        .anchor=${this.anchor}
      >
        <div part="body" class="body">
          <slot></slot>
        </div>
      </wa-popup>
    `}};E.css=so;E.dependencies={"wa-popup":b};m([pt("slot:not([name])")],E.prototype,"defaultSlot",2);m([pt(".body")],E.prototype,"body",2);m([pt("wa-popup")],E.prototype,"popup",2);m([g()],E.prototype,"placement",2);m([g({type:Boolean,reflect:!0})],E.prototype,"disabled",2);m([g({type:Number})],E.prototype,"distance",2);m([g({type:Boolean,reflect:!0})],E.prototype,"open",2);m([g({type:Number})],E.prototype,"skidding",2);m([g({attribute:"show-delay",type:Number})],E.prototype,"showDelay",2);m([g({attribute:"hide-delay",type:Number})],E.prototype,"hideDelay",2);m([g()],E.prototype,"trigger",2);m([g({attribute:"without-arrow",type:Boolean,reflect:!0})],E.prototype,"withoutArrow",2);m([g()],E.prototype,"for",2);m([io()],E.prototype,"anchor",2);m([Yt("open",{waitUntilFirstUpdate:!0})],E.prototype,"handleOpenChange",1);m([Yt("for")],E.prototype,"handleForChange",1);m([Yt(["distance","placement","skidding"])],E.prototype,"handleOptionsChange",1);m([Yt("disabled")],E.prototype,"handleDisabledChange",1);E=m([ot("wa-tooltip")],E);var nr=T`
  :host {
    --track-width: 2px;
    --track-color: var(--wa-color-neutral-fill-normal);
    --indicator-color: var(--wa-color-brand-fill-loud);
    --speed: 2s;
    --size: 1em;

    /*
      Resizing a spinner element using anything but font-size will break the animation because the animation uses em
      units. Therefore, if a spinner is used in a flex container without \`flex: none\` applied, the spinner can
      grow/shrink and break the animation. The use of \`flex: none\` on the host element prevents this by always having
      the spinner sized according to its actual dimensions.
    */
    flex: none;
    display: inline-flex;
    width: var(--size);
    height: var(--size);
  }

  svg {
    width: 100%;
    height: 100%;
    aspect-ratio: 1;
    animation: spin var(--speed) linear infinite;
  }

  .track,
  .indicator {
    --radius: calc(var(--size) / 2 - var(--track-width) / 2);
    --circumference: calc(var(--radius) * 2 * 3.141592654);

    cx: calc(var(--size) / 2);
    cy: calc(var(--size) / 2);
    r: var(--radius);
    fill: none;
    stroke-width: var(--track-width);
  }

  .track {
    stroke: var(--track-color);
  }

  .indicator {
    stroke: var(--indicator-color);
    stroke-linecap: round;
    stroke-dasharray: calc(0.597 * var(--circumference)), calc(0.796 * var(--circumference));
    stroke-dashoffset: calc(-0.04 * var(--circumference));
    animation: dash 1.5s ease-in-out infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  @keyframes dash {
    0% {
      stroke-dasharray: calc(0.008 * var(--circumference)), calc(1.194 * var(--circumference));
      stroke-dashoffset: 0;
    }
    50% {
      stroke-dasharray: calc(0.716 * var(--circumference)), calc(1.194 * var(--circumference));
      stroke-dashoffset: calc(-0.278 * var(--circumference));
    }
    100% {
      stroke-dasharray: calc(0.716 * var(--circumference)), calc(1.194 * var(--circumference));
      stroke-dashoffset: calc(-0.987 * var(--circumference));
    }
  }
`;var de=class extends M{constructor(){super(...arguments),this.localize=new te(this)}render(){return X`
      <svg
        part="base spinner"
        role="progressbar"
        aria-label=${this.localize.term("loading")}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle class="track" />
        <circle class="indicator" />
      </svg>
    `}};de.css=nr;de=m([ot("wa-spinner")],de);globalThis.DevConsoleWebAwesome=Object.freeze({version:"3.14.0",components:["badge","tooltip","spinner"]});})();
